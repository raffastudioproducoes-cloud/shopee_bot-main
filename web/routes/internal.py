"""
Rotas internas — chamadas apenas pela API nova (api/), nunca por browser.

Protegidas por segredo compartilhado (header X-Internal-Secret), não por
sessão de usuário: quem chama é outro processo backend, sem cookie.

Existe porque add_job/remove_job/run_job (shopee_bot.scheduler) dependem
de um singleton `_scheduler` (APScheduler) que só é inicializado uma vez
por processo, no `post_fork` do gunicorn do Flask. Rodar `scheduler.init()`
também no processo da API nova arriscaria dois `_scheduler` publicando o
mesmo job em duplicata. Em vez de importar o módulo scheduler diretamente,
a API nova chama estas rotas por HTTP — só o Flask tem `_scheduler` vivo.

Mesma razão pra validate_shopee: apis/shopee.py importa shopee_bot.utils
e shopee_bot.returnable_thread, que só existem registrados no processo
Flask (alias de pacote via Docker ou conftest.py) — chamar por HTTP evita
precisar replicar esse alias na API nova.
"""

import hmac
import os
from datetime import datetime, time as dt_time
from functools import wraps

from flask import Blueprint, request, jsonify

from shopee_bot.scheduler import add_job, remove_job, run_job
from shopee_bot.apis import shopee as ShopeeAPI
from shopee_bot.apis import x as XAPI
from shopee_bot.apis import facebook as FacebookAPI
from shopee_bot.apis import threads as ThreadsAPI
from shopee_bot.apis import instagram as InstagramAPI
from shopee_bot.apis import tiktok as TikTokAPI
from shopee_bot.database.schedulers import NETWORK_FUNC_MAP

internal_bp = Blueprint("internal", __name__, url_prefix="/internal")

# Whitelist do `func` aceito por create_job: só os nomes que o
# scheduler resolve via globals() (scheduler/__init__.py) — sem isso,
# um `func` arbitrário na requisição (mesmo autenticada pelo segredo
# interno) vira uma chamada arbitrária a qualquer símbolo importado
# naquele módulo. Reusa NETWORK_FUNC_MAP em vez de duplicar a lista.
ALLOWED_FUNCS = set(NETWORK_FUNC_MAP.values())


def _require_internal_secret(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        secret = os.environ.get("INTERNAL_API_SECRET")
        given = request.headers.get("X-Internal-Secret")
        if not secret or not given or not hmac.compare_digest(
            given.encode("utf-8"), secret.encode("utf-8")
        ):
            return jsonify({"error": "Não autorizado"}), 403
        return fn(*args, **kwargs)
    return wrapper


def _parse_datetime(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def _parse_time(value):
    if not value:
        return None
    hour, minute = value.split(":")
    return dt_time(hour=int(hour), minute=int(minute))


@internal_bp.post("/scheduler/jobs")
@_require_internal_secret
def create_job():
    body = request.get_json(force=True)
    user_id = body["user_id"]
    func = body["func"]
    if func not in ALLOWED_FUNCS:
        # jsonify direto, não abort(): o errorhandler(Exception) global
        # (web/__init__.py) engole HTTPException e devolve 500 genérico
        # — mesmo padrão já usado em _require_internal_secret acima.
        return jsonify({"error": f"func '{func}' não permitido"}), 400
    job = {
        "post_id": body["post_id"],
        "func": func,
        "trigger": body["trigger"],
        "time": _parse_time(body.get("time")),
        "day_of_week": body.get("day_of_week"),
        "start_date": _parse_datetime(body.get("start_date")),
        "run_date": _parse_datetime(body.get("run_date")),
        "profile_id": body.get("profile_id"),
    }
    job_id = add_job(user_id, job)
    return jsonify({"job_id": str(job_id)}), 201


@internal_bp.delete("/scheduler/jobs/<job_id>")
@_require_internal_secret
def delete_job(job_id):
    body = request.get_json(force=True)
    remove_job(body["user_id"], job_id)
    return jsonify({}), 200


@internal_bp.post("/scheduler/jobs/<job_id>/run")
@_require_internal_secret
def run_job_now(job_id):
    run_job(job_id)
    return jsonify({}), 200


@internal_bp.post("/shopee/validate")
@_require_internal_secret
def validate_shopee():
    body = request.get_json(force=True)
    try:
        valid = ShopeeAPI.query_auth_validate(body["app_id"], body["secret"])
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 200
    return jsonify({"valid": bool(valid)}), 200


# "Testar conexão" (luz verde/amarela do sinalizador em cada credencial) —
# dispatcher genérico em vez de uma rota por rede: cada rede chama a API real
# via apis/*.py (só existem "vivas" aqui, no processo Flask — ver docstring
# do módulo) e traduz o resultado pro par (state, message) que a API nova
# grava em credential_checks. Sempre 200 (menos rede desconhecida): erro de
# validação é resultado esperado do teste, não falha da rota em si.
@internal_bp.post("/credentials/<network>/validate")
@_require_internal_secret
def validate_credential(network):
    body = request.get_json(force=True)

    def ok(message):
        return jsonify({"state": "ok", "message": message}), 200

    def error(message):
        return jsonify({"state": "error", "message": str(message)[:300]}), 200

    try:
        if network == "shopee":
            valid = ShopeeAPI.query_auth_validate(body["app_id"], body["secret"])
            return ok("Credencial válida") if valid else error("Credencial inválida")

        if network == "x":
            XAPI.validate_credentials(body["app_id"], body["secret"])
            if not body.get("user_access_token"):
                return error(
                    "App ID/Secret válidos, mas falta autorizar via OAuth "
                    "(Conectar X) — sem isso não é possível publicar."
                )
            return ok("Conectado")

        if network == "facebook":
            if not body.get("page_access_token"):
                return error(
                    "App único válido, mas falta autorizar via OAuth "
                    "(Conectar Facebook) — sem isso não é possível publicar."
                )
            FacebookAPI.validate_page_access_token(
                body["page_access_token"], body.get("page_id")
            )
            return ok("Conectado")

        if network == "threads":
            if not body.get("access_token"):
                return error("Nenhum token salvo")
            ThreadsAPI.get_user_id(body["access_token"])
            return ok("Conectado")

        if network == "instagram":
            InstagramAPI.validate_credentials(
                body["app_id"], body["secret"], body.get("user_access_token")
            )
            if not body.get("user_access_token"):
                return error(
                    "App ID/Secret válidos, mas falta autorizar via OAuth "
                    "(Conectar Instagram) — sem isso não é possível publicar."
                )
            return ok("Conectado")

        if network == "tiktok":
            if not body.get("user_access_token"):
                return error(
                    "Client Key/Secret salvos, mas falta autorizar via OAuth "
                    "(Conectar TikTok) — sem isso não é possível publicar."
                )
            TikTokAPI.get_user_info(body["user_access_token"])
            return ok("Conectado")

        if network == "kwai":
            return error(
                "Kwai não tem API pública documentada para validar credenciais."
            )

        return jsonify({"error": f"Rede '{network}' não suportada"}), 400
    except Exception as e:
        return error(e)

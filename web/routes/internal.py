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

from flask import Blueprint, request, jsonify, current_app

from shopee_bot.scheduler import add_job, remove_job, run_job, scheduler_enabled, scheduler_ready
from shopee_bot.apis import shopee as ShopeeAPI
from shopee_bot.apis import x as XAPI
from shopee_bot.apis import facebook as FacebookAPI
from shopee_bot.apis import threads as ThreadsAPI
from shopee_bot.apis import instagram as InstagramAPI
from shopee_bot.apis import tiktok as TikTokAPI
from shopee_bot.database.schedulers import NETWORK_FUNC_MAP
from shopee_bot.utils.timezones import normalize_timezone

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


def _require_scheduler_role(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not scheduler_enabled():
            return jsonify({"error": "Agendador indisponível"}), 503
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


def _parse_days_of_week(value):
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 7
        or len(set(value)) != len(value)
        or any(not isinstance(day, int) or day < 0 or day > 6 for day in value)
    ):
        raise ValueError("days_of_week deve ter de um a sete dias únicos entre 0 e 6")
    return value


@internal_bp.get("/scheduler/status")
@_require_internal_secret
def scheduler_status():
    # Endpoint somente de leitura para impedir upload/criação sem worker.
    return jsonify({"available": scheduler_ready()}), 200


@internal_bp.post("/scheduler/jobs")
@_require_internal_secret
@_require_scheduler_role
def create_job():
    body = request.get_json(force=True)
    user_id = body["user_id"]
    func = body["func"]
    if func not in ALLOWED_FUNCS:
        # jsonify direto, não abort(): o errorhandler(Exception) global
        # (web/__init__.py) engole HTTPException e devolve 500 genérico
        # — mesmo padrão já usado em _require_internal_secret acima.
        return jsonify({"error": f"func '{func}' não permitido"}), 400
    profile_id = body.get("profile_id")
    if not profile_id:
        return jsonify({"error": "profile_id obrigatorio"}), 400
    try:
        days_of_week = _parse_days_of_week(body.get("days_of_week"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if days_of_week is not None and body.get("day_of_week") not in (None, days_of_week[0]):
        return jsonify({"error": "day_of_week deve corresponder ao primeiro item de days_of_week"}), 400
    timezone_name = body.get("timezone")
    if timezone_name is not None:
        try:
            timezone_name = normalize_timezone(timezone_name)
        except ValueError:
            return jsonify({"error": "Fuso horário inválido"}), 400
    job = {
        "post_id": body["post_id"],
        "func": func,
        "trigger": body["trigger"],
        "time": _parse_time(body.get("time")),
        "day_of_week": body.get("day_of_week"),
        "days_of_week": days_of_week,
        "start_date": _parse_datetime(body.get("start_date")),
        "run_date": _parse_datetime(body.get("run_date")),
        "profile_id": profile_id,
        "timezone": timezone_name,
    }
    try:
        job_id = add_job(user_id, job)
    except (TypeError, ValueError):
        current_app.logger.warning("Agenda recusada por parâmetros inválidos", exc_info=True)
        return jsonify({"error": "Parâmetros inválidos para o agendamento"}), 400
    except Exception:
        # O motivo técnico permanece no servidor; não retornar traceback,
        # DSN, credencial nem dados do cliente ao navegador.
        current_app.logger.exception("Falha interna ao criar agenda (%s)", func)
        return jsonify({"error": "Falha interna ao criar agendamento"}), 500
    if not job_id:
        current_app.logger.error("Agendador concluiu sem retornar ID (func=%s)", func)
        return jsonify({"error": "Agendador não confirmou a criação"}), 500
    return jsonify({"job_id": str(job_id)}), 201


@internal_bp.delete("/scheduler/jobs/<job_id>")
@_require_internal_secret
@_require_scheduler_role
def delete_job(job_id):
    body = request.get_json(force=True)
    remove_job(body["user_id"], job_id)
    return jsonify({}), 200


@internal_bp.post("/scheduler/jobs/<job_id>/run")
@_require_internal_secret
@_require_scheduler_role
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

    # `refreshed_tokens`: tokens renovados durante o teste (X/TikTok rotacionam
    # o refresh token) — a API nova persiste; nunca vão pro usuário.
    def ok(message, refreshed=None):
        return jsonify({"state": "ok", "message": message, "refreshed_tokens": refreshed}), 200

    def error(message, refreshed=None):
        message = str(message)
        # exceções de rede (requests) citam a URL, que leva o token em query
        for key in ("user_access_token", "refresh_token", "access_token", "page_access_token", "secret"):
            if body.get(key):
                message = message.replace(str(body[key]), "***")
        return jsonify({
            "state": "error", "message": message[:300], "refreshed_tokens": refreshed,
        }), 200

    try:
        if network == "shopee":
            valid = ShopeeAPI.query_auth_validate(body["app_id"], body["secret"])
            return ok("Credencial válida") if valid else error("Credencial inválida")

        if network == "x":
            if not body.get("user_access_token"):
                return error("Falta autorizar via OAuth (Conectar X) — sem isso não é possível publicar.")
            _, refreshed = XAPI.validate_user_token(
                body["app_id"], body["secret"], body["user_access_token"], body.get("refresh_token")
            )
            return ok("Conectado", refreshed)

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
            if not body.get("user_access_token"):
                return error("Falta autorizar via OAuth (Conectar Instagram) — sem isso não é possível publicar.")
            InstagramAPI.validate_user_token(body["user_access_token"], body.get("ig_user_id"))
            return ok("Conectado")

        if network == "tiktok":
            if not body.get("user_access_token"):
                return error("Falta autorizar via OAuth (Conectar TikTok) — sem isso não é possível publicar.")
            _, refreshed = TikTokAPI.validate_user_token(
                body["app_id"], body["secret"], body["user_access_token"], body.get("refresh_token")
            )
            return ok("Conectado", refreshed)

        if network == "kwai":
            return error(
                "Kwai não tem API pública documentada para validar credenciais."
            )

        return jsonify({"error": f"Rede '{network}' não suportada"}), 400
    except Exception as e:
        return error(e, getattr(e, "refreshed", None))

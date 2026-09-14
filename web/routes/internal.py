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

import os
from datetime import datetime, time as dt_time
from functools import wraps

from flask import Blueprint, request, jsonify

from shopee_bot.scheduler import add_job, remove_job, run_job
from shopee_bot.apis import shopee as ShopeeAPI

internal_bp = Blueprint("internal", __name__, url_prefix="/internal")


def _require_internal_secret(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        secret = os.environ.get("INTERNAL_API_SECRET")
        given = request.headers.get("X-Internal-Secret")
        if not secret or not given or given != secret:
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
    job = {
        "post_id": body["post_id"],
        "func": body["func"],
        "trigger": body["trigger"],
        "time": _parse_time(body.get("time")),
        "day_of_week": body.get("day_of_week"),
        "start_date": _parse_datetime(body.get("start_date")),
        "run_date": _parse_datetime(body.get("run_date")),
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

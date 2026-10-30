
import hmac
import os

from flask import Blueprint, request

from shopee_bot.scheduler import request_wakeup


cron_wakeup_bp = Blueprint("cron_wakeup", __name__)


@cron_wakeup_bp.post("/_ops/scheduler/wake")
def cron_wakeup():
    expected = os.environ.get("ORBITAL_WAKE_SECRET", "")
    authorization = request.headers.get("Authorization", "")

    # Falha fechada: segredo ausente também bloqueia a rota.
    if not expected or not authorization.startswith("Bearer "):
        return "", 404

    provided = authorization[len("Bearer "):]

    if not hmac.compare_digest(provided, expected):
        return "", 404

    # Não cria jobs e não recebe dados de usuários.
    # Apenas solicita uma verificação ao agendador existente.
    if not request_wakeup():
        return "", 503

    return "", 204

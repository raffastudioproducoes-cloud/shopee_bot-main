"""Autorização Shopee Vídeo pronta para uso: token válido, renovação e reconexão.

Usado pelo roteador (status/refresh), pela lista de credenciais, pelo
publicador (scheduler/bot_post_shopee_video.py) e pela rotina periódica.
access_token vale 4 h; refresh_token vale 30 dias e é de USO ÚNICO por
user_id: o par novo é gravado num único UPDATE condicionado ao refresh
antigo. Se a Shopee recusar o refresh ou a gravação falhar depois dele, a
autorização se perde: marca needs_reconnect (migração 105). Nunca logar tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from database.scheduler_environment import current_environment
from . import shopee_video_oauth as oauth
from .crypto import decrypt, encrypt
from .database import supabase
from .profiles import scope_owner

logger = logging.getLogger(__name__)

APP_TABLE = "platform_shopee_video_apps"
USER_TABLE = "shopee_video_authorizations"
AUTH_COLUMNS = ("partner_id,shopee_user_id,access_token,refresh_token,expires_at,"
                "refresh_expires_at,needs_reconnect")
ACCESS_TOKEN_SECONDS = 14400
REFRESH_TOKEN_DAYS = 30
REFRESH_MARGIN = timedelta(minutes=10)
JOB_ACCESS_WINDOW = timedelta(hours=1)
JOB_REFRESH_WINDOW = timedelta(days=5)
RECONNECT_MESSAGE = "Autorização da Shopee Vídeo expirada — reconecte em Credenciais"
NOT_CONFIGURED_MESSAGE = "Shopee Vídeo ainda não está configurada pelo administrador."


class ShopeeVideoNotConfigured(Exception):
    """Aplicativo global ausente/desligado ou perfil sem autorização."""


class ShopeeVideoReconnectRequired(Exception):
    """Refresh recusado ou perdido: o usuário precisa reconectar."""


@dataclass(frozen=True)
class ValidAuthorization:
    partner_id: int
    partner_key: str
    shopee_user_id: int
    access_token: str
    sandbox: bool


def parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def access_expiry(token_data: dict, now: datetime) -> datetime:
    """Algumas respostas usam duração, outras timestamp absoluto de segundos."""
    try:
        value = int(token_data.get("expire_in", ACCESS_TOKEN_SECONDS))
    except (ValueError, TypeError):
        value = ACCESS_TOKEN_SECONDS
    if value > 1_000_000_000:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return now + timedelta(seconds=max(60, min(value, ACCESS_TOKEN_SECONDS)))


def token_columns(token_data: dict, now: datetime) -> dict:
    """Par novo cifrado + validade; sempre gravado junto (refresh é de uso único)."""
    return {
        "access_token": encrypt(token_data["access_token"]),
        "refresh_token": encrypt(token_data["refresh_token"]),
        "expires_at": access_expiry(token_data, now).isoformat(),
        "refresh_expires_at": (now + timedelta(days=REFRESH_TOKEN_DAYS)).isoformat(),
        "needs_reconnect": False, "reconnect_reason": None,
        "updated_at": now.isoformat(),
    }


def app_row(client=None) -> dict | None:
    """`client`: o Supabase do chamador (roteadores que já têm o seu)."""
    result = (client or supabase).table(APP_TABLE).select(
        "partner_id,partner_key,sandbox,enabled"
    ).eq("environment", current_environment()).maybe_single().execute()
    return result.data if result else None


def is_configured(row: dict | None) -> bool:
    return bool(row and row.get("enabled") and row.get("partner_id") and row.get("partner_key"))


def app_config() -> dict:
    """App global decifrado; ShopeeVideoNotConfigured se ausente/desligado."""
    row = app_row()
    if not is_configured(row):
        raise ShopeeVideoNotConfigured(NOT_CONFIGURED_MESSAGE)
    try:
        return {"partner_id": int(row["partner_id"]), "partner_key": decrypt(row["partner_key"]),
                "sandbox": bool(row["sandbox"])}
    except Exception:
        logger.error("Erro ao decifrar chave global Shopee Vídeo")
        raise ShopeeVideoNotConfigured("Configuração de Shopee Vídeo indisponível.") from None


def auth_row(user_id, profile_id: str, client=None) -> dict | None:
    result = scope_owner((client or supabase).table(USER_TABLE).select(AUTH_COLUMNS), user_id, profile_id).eq(
        "environment", current_environment(),
    ).maybe_single().execute()
    return result.data if result else None


def mark_needs_reconnect(user_id, profile_id: str, reason: str = RECONNECT_MESSAGE) -> None:
    try:
        scope_owner(supabase.table(USER_TABLE).update({
            "needs_reconnect": True, "reconnect_reason": reason[:200],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }), user_id, profile_id).eq("environment", current_environment()).execute()
    except Exception as err:
        logger.warning("Shopee Vídeo: não marcou reconexão: %s", type(err).__name__)


def _store_refreshed(user_id, profile_id: str, row: dict, result: dict, now: datetime) -> dict:
    """UPDATE único condicionado ao refresh antigo; sem linha = par perdido."""
    columns = token_columns(result, now)
    saved = scope_owner(supabase.table(USER_TABLE).update(columns), user_id, profile_id).eq(
        "environment", current_environment(),
    ).eq("partner_id", row["partner_id"]).eq("refresh_token", row["refresh_token"]).execute()
    if not saved.data:
        raise RuntimeError("Autorização não encontrada para gravar a renovação")
    return {**row, **columns}


def _lost(user_id, profile_id: str, what: str) -> ShopeeVideoReconnectRequired:
    logger.warning("Shopee Vídeo: %s; autorização marcada para reconexão", what)
    mark_needs_reconnect(user_id, profile_id)
    return ShopeeVideoReconnectRequired(RECONNECT_MESSAGE)


def refresh_authorization(user_id, profile_id: str, config: dict, row: dict, now: datetime) -> dict:
    """Renova e grava o par novo. Transitório → oauth.ShopeeVideoOAuthError."""
    try:
        result = oauth.refresh_token_sync(
            config["partner_id"], config["partner_key"], int(row["shopee_user_id"]),
            decrypt(row["refresh_token"]), sandbox=config["sandbox"],
        )
    except oauth.ShopeeVideoRefreshRejected:
        latest = auth_row(user_id, profile_id)
        if latest and latest.get("refresh_token") != row["refresh_token"] and not latest.get("needs_reconnect"):
            return latest  # outro worker renovou primeiro; usa o par gravado por ele
        raise _lost(user_id, profile_id, "refresh recusado pela Shopee") from None
    try:
        return _store_refreshed(user_id, profile_id, row, result, now)
    except Exception as err:
        raise _lost(user_id, profile_id, f"par novo não gravado ({type(err).__name__})") from None


def _usable_row(user_id, profile_id: str, config: dict, now: datetime) -> dict:
    row = auth_row(user_id, profile_id) if profile_id else None
    if not row or row.get("partner_id") != config["partner_id"]:
        raise ShopeeVideoNotConfigured("Conecte a conta Shopee Vídeo em Credenciais.")
    refresh_until = parse_datetime(row.get("refresh_expires_at"))
    if row.get("needs_reconnect") or not refresh_until or refresh_until <= now:
        raise ShopeeVideoReconnectRequired(RECONNECT_MESSAGE)
    return row


def get_valid_authorization(user_id, profile_id: str, *, now: datetime | None = None) -> ValidAuthorization:
    """Token válido por mais de 10 min; senão renova e grava o par novo antes de devolver."""
    now = now or datetime.now(timezone.utc)
    config = app_config()
    row = _usable_row(user_id, profile_id, config, now)
    expires = parse_datetime(row.get("expires_at"))
    if not row.get("access_token") or not expires or expires - now < REFRESH_MARGIN:
        row = refresh_authorization(user_id, profile_id, config, row, now)
    return ValidAuthorization(config["partner_id"], config["partner_key"], int(row["shopee_user_id"]),
                              decrypt(row["access_token"]), config["sandbox"])


def connection_state(user_id, profile_id: str | None, *, now: datetime | None = None,
                     client=None) -> dict:
    """Estado sem tokens: configured, connected, token_valid, needs_reconnect, sandbox, publishing_enabled."""
    now = now or datetime.now(timezone.utc)
    config = app_row(client)
    configured = is_configured(config)
    row = auth_row(user_id, profile_id, client) if profile_id else None
    connected = bool(configured and row and row.get("refresh_token")
                     and row.get("partner_id") == config.get("partner_id"))
    refresh_until = parse_datetime(row.get("refresh_expires_at")) if connected else None
    needs = bool(connected and (row.get("needs_reconnect") or not refresh_until or refresh_until <= now))
    expires = parse_datetime(row.get("expires_at")) if connected else None
    return {
        "configured": configured,
        "connected": connected,
        "token_valid": bool(connected and not needs and row.get("access_token") and expires and expires > now),
        "needs_reconnect": needs,
        "sandbox": bool(config.get("sandbox")) if configured else None,
        # Token válido OU renovável (refresh dentro do prazo e não recusado).
        "publishing_enabled": bool(connected and not needs),
    }


def _expiring_rows(now: datetime) -> list[dict]:
    # ponytail: filtra em Python; poucas autorizações por ambiente. Filtro SQL se crescer.
    rows = supabase.table(USER_TABLE).select(f"user_id,profile_id,{AUTH_COLUMNS}").eq(
        "environment", current_environment(),
    ).eq("needs_reconnect", False).execute().data or []
    due = []
    for row in rows:
        expires = parse_datetime(row.get("expires_at"))
        refresh_until = parse_datetime(row.get("refresh_expires_at"))
        if not refresh_until or refresh_until <= now:
            continue  # já expirou: só reconexão resolve
        if not expires or expires - now < JOB_ACCESS_WINDOW or refresh_until - now < JOB_REFRESH_WINDOW:
            due.append(row)
    return due


def refresh_expiring(now: datetime | None = None) -> dict:
    """Rotina periódica: renova access < 1 h e refresh < 5 dias do vencimento."""
    now = now or datetime.now(timezone.utc)
    try:
        config = app_config()
    except ShopeeVideoNotConfigured:
        return {"refreshed": 0, "reconnect": 0, "errors": 0}
    counts = {"refreshed": 0, "reconnect": 0, "errors": 0}
    for row in _expiring_rows(now):
        if row.get("partner_id") != config["partner_id"]:
            continue
        try:
            refresh_authorization(row["user_id"], row["profile_id"], config, row, now)
            counts["refreshed"] += 1
        except ShopeeVideoReconnectRequired:
            counts["reconnect"] += 1
        except Exception as err:  # transitório: tenta de novo na próxima rodada
            logger.warning("Shopee Vídeo: renovação adiada: %s", type(err).__name__)
            counts["errors"] += 1
    return counts

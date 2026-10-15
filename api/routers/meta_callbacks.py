"""Callbacks publicos da Meta/Threads.

Recebem `signed_request` (form-urlencoded), validam HMAC-SHA256 com o
app secret global e desconectam as credenciais locais sem exigir JWT.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request

from .. import instagram_oauth, threads_oauth
from ..audit_log import log_action
from ..audit_trail import record_audit_event
from ..config import settings
from ..database import supabase
from .auth import client_ip

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["meta-callbacks"])

_MAX_BODY_BYTES = 4096
_SIGNED_REQUEST_MAX_AGE_SECONDS = 60 * 60
_SIGNED_REQUEST_FUTURE_SKEW_SECONDS = 5 * 60
_REPLAY_MAX_KEYS = 2048
_INVALID_SIGNATURE_LIMIT = 20
_INVALID_SIGNATURE_WINDOW_SECONDS = 15 * 60
_STATUS_LIMIT = 120
_STATUS_WINDOW_SECONDS = 60
_RATE_MAX_KEYS = 2048

_META_TARGETS = (
    ("facebook", "facebook_credentials", ("fb_user_id",)),
    ("instagram", "instagram_credentials", ("fb_user_id",)),
)
_THREADS_TARGETS = (("threads", "threads_credentials", ("t_user_id",)),)

_DEAUTHORIZE_UPDATES = {
    "facebook": {"page_access_token": None, "status": False},
    "instagram": {"user_access_token": None, "status": False},
    "threads": {"access_token": None, "status": False},
}
_DELETE_UPDATES = {
    "facebook": {
        "app_id": None,
        "secret": None,
        "fb_user_id": None,
        "page_id": None,
        "page_name": None,
        "page_access_token": None,
        "status": False,
    },
    "instagram": {
        "app_id": None,
        "secret": None,
        "fb_user_id": None,
        "ig_user_id": None,
        "user_access_token": None,
        "status": False,
    },
    "threads": {"t_user_id": None, "access_token": None, "status": False},
}

_rate_attempts: dict[str, list[float]] = {}

# ponytail: cache de replay em memoria de processo (TTL = janela de issued_at).
# Com varios workers cada um tem o seu; o efeito colateral dos callbacks
# (desconectar/limpar) e idempotente, entao o risco residual e so reprocessar
# uma vez por worker. Upgrade: tabela no Postgres se precisar de garantia global.
_replay_cache: dict[tuple, tuple[float, dict]] = {}


def _recall_replay(key: tuple) -> dict | None:
    entry = _replay_cache.get(key)
    if not entry:
        return None
    if entry[0] < time.time():
        del _replay_cache[key]
        return None
    return entry[1]


def _remember_replay(key: tuple, response: dict) -> None:
    now = time.time()
    for old in [k for k, (exp, _) in _replay_cache.items() if exp < now]:
        del _replay_cache[old]
    while len(_replay_cache) >= _REPLAY_MAX_KEYS:
        del _replay_cache[min(_replay_cache, key=lambda k: _replay_cache[k][0])]
    ttl = _SIGNED_REQUEST_MAX_AGE_SECONDS + _SIGNED_REQUEST_FUTURE_SKEW_SECONDS
    _replay_cache[key] = (now + ttl, response)


def _check_memory_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    now = time.time()
    cutoff = now - window_seconds
    for existing_key in list(_rate_attempts):
        _rate_attempts[existing_key] = [ts for ts in _rate_attempts[existing_key] if ts >= cutoff]
        if not _rate_attempts[existing_key]:
            del _rate_attempts[existing_key]
    while len(_rate_attempts) >= _RATE_MAX_KEYS:
        oldest = min(_rate_attempts, key=lambda item: _rate_attempts[item][-1])
        del _rate_attempts[oldest]
    attempts = _rate_attempts.setdefault(key, [])
    if len(attempts) >= limit:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde antes de tentar novamente.")
    attempts.append(now)


def _record_invalid_signature(request: Request) -> None:
    _check_memory_rate_limit(
        f"invalid-signature:{request.url.path}:{client_ip(request)}",
        limit=_INVALID_SIGNATURE_LIMIT,
        window_seconds=_INVALID_SIGNATURE_WINDOW_SECONDS,
    )


def _check_status_rate_limit(request: Request) -> None:
    _check_memory_rate_limit(
        f"status:{client_ip(request)}",
        limit=_STATUS_LIMIT,
        window_seconds=_STATUS_WINDOW_SECONDS,
    )


def _b64url_decode(value: str) -> bytes:
    if not value or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for c in value):
        raise ValueError("invalid base64url")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _verify_signed_request(signed_request: str, secret: str | None) -> dict:
    if not secret:
        logger.warning("Callback Meta/Threads recebido sem app secret configurado; fechado por seguranca")
        raise HTTPException(status_code=503, detail="Callback indisponivel")

    try:
        signature_b64, payload_b64 = signed_request.split(".", 1)
        signature = _b64url_decode(signature_b64)
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="signed_request invalido") from None

    if not isinstance(payload, dict) or str(payload.get("algorithm", "")).upper() != "HMAC-SHA256":
        raise HTTPException(status_code=400, detail="signed_request invalido")

    try:
        issued_at = float(payload.get("issued_at"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="signed_request invalido") from None
    age = time.time() - issued_at
    if age > _SIGNED_REQUEST_MAX_AGE_SECONDS or age < -_SIGNED_REQUEST_FUTURE_SKEW_SECONDS:
        raise HTTPException(status_code=400, detail="signed_request invalido")

    expected = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="signed_request invalido")

    user_id = payload.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=400, detail="signed_request invalido")
    return {"user_id": user_id.strip(), "issued_at": issued_at}


async def _signed_payload(request: Request, secret: str | None) -> dict:
    content_length = request.headers.get("content-length")
    try:
        too_large = bool(content_length and int(content_length) > _MAX_BODY_BYTES)
    except ValueError:
        too_large = False
    if too_large:
        raise HTTPException(status_code=413, detail="Corpo muito grande")
    body = await request.body()
    if len(body) > _MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Corpo muito grande")
    form = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True, strict_parsing=False)
    values = form.get("signed_request") or []
    if len(values) != 1:
        _record_invalid_signature(request)
        raise HTTPException(status_code=400, detail="signed_request invalido")
    try:
        return _verify_signed_request(values[0], secret)
    except HTTPException as exc:
        if exc.status_code == 400:
            _record_invalid_signature(request)
        raise


def _external_hash(provider: str, external_user_id: str) -> str:
    key = hmac.new(
        settings.api_secret_key.encode("utf-8"),
        b"data-deletion-v1",
        hashlib.sha256,
    ).digest()
    return hmac.new(
        key,
        f"{provider}:{external_user_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _delete_credential_checks(rows: list[dict], network: str) -> None:
    for row in rows:
        query = supabase.table("credential_checks").delete().eq("user_id", row.get("user_id")).eq("network", network)
        profile_id = row.get("profile_id")
        if profile_id:
            query = query.eq("profile_id", profile_id)
        else:
            query = query.is_("profile_id", "null")
        query.execute()


def _record_disconnect_audits(rows: list[dict], network: str, event: str) -> None:
    for row in rows:
        profile_id = row.get("profile_id")
        record_audit_event(
            "social_credential",
            f"{network}:{row.get('id')}",
            str(row.get("user_id")),
            event,
            {"provider": network, "connected": True},
            {"provider": network, "connected": False},
            profile_id=str(profile_id) if profile_id else None,
        )


def _update_credentials(table: str, rows: list[dict], update_data: dict) -> int:
    affected = 0
    for row in rows:
        result = supabase.table(table).update(update_data).eq("id", row.get("id")).execute()
        updated = result.data or [row]
        affected += len(updated)
    return affected


def _disconnect_by_external_id(targets, external_user_id: str, *, delete_data: bool, event: str) -> int:
    affected = 0
    for network, table, id_columns in targets:
        rows = []
        seen_ids = set()
        for id_column in id_columns:
            matched = (
                supabase.table(table)
                .select("id, user_id, profile_id")
                .eq(id_column, external_user_id)
                .execute()
                .data
                or []
            )
            for row in matched:
                row_id = row.get("id")
                if row_id in seen_ids:
                    continue
                seen_ids.add(row_id)
                rows.append(row)
        if not rows:
            continue
        update_data = _DELETE_UPDATES[network] if delete_data else _DEAUTHORIZE_UPDATES[network]
        if delete_data:
            _delete_credential_checks(rows, network)
            _record_disconnect_audits(rows, network, event)
            affected += _update_credentials(table, rows, update_data)
        else:
            affected += _update_credentials(table, rows, update_data)
            _delete_credential_checks(rows, network)
            _record_disconnect_audits(rows, network, event)
    return affected


def _status_url(code: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/api/meta/data-deletion/status?code={code}"


def _existing_deletion_request(provider: str, external_user_hash: str) -> dict | None:
    result = (
        supabase.table("data_deletion_requests")
        .select("id, confirmation_code, status")
        .eq("provider", provider)
        .eq("external_user_hash", external_user_hash)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data if result and result.data else []
    return rows[0] if rows else None


def _begin_deletion_request(provider: str, external_user_hash: str) -> dict:
    existing = _existing_deletion_request(provider, external_user_hash)
    if existing:
        previous_status = existing.get("status")
        result = (
            supabase.table("data_deletion_requests")
            .update({"status": "received", "completed_at": None})
            .eq("confirmation_code", existing["confirmation_code"])
            .execute()
        )
        updated = result.data or []
        row = updated[0] if updated else {**existing, "status": "received", "completed_at": None}
        return {**row, "_previous_status": previous_status}
    row = {
        "confirmation_code": secrets.token_urlsafe(24),
        "provider": provider,
        "external_user_hash": external_user_hash,
        "status": "received",
        "completed_at": None,
    }
    try:
        result = supabase.table("data_deletion_requests").insert(row).execute()
    except Exception:
        existing = _existing_deletion_request(provider, external_user_hash)
        if existing:
            return _begin_deletion_request(provider, external_user_hash)
        raise
    return result.data[0]


def _complete_deletion_request(confirmation_code: str, status: str) -> None:
    supabase.table("data_deletion_requests").update(
        {"status": status, "completed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("confirmation_code", confirmation_code).execute()


async def _handle_disconnect(request: Request, *, secret: str | None, targets, event: str) -> dict:
    payload = await _signed_payload(request, secret)
    replay_key = (event, payload["user_id"], payload["issued_at"])
    if (cached := _recall_replay(replay_key)) is not None:
        return cached
    affected = _disconnect_by_external_id(targets, payload["user_id"], delete_data=False, event=event)
    log_action(event, f"provider={event} matched={bool(affected)}")
    response = {"status": "received"}
    _remember_replay(replay_key, response)
    return response


async def _handle_delete(request: Request, *, secret: str | None, targets, provider: str, event: str) -> dict:
    payload = await _signed_payload(request, secret)
    replay_key = (event, payload["user_id"], payload["issued_at"])
    if (cached := _recall_replay(replay_key)) is not None:
        return cached
    external_user_hash = _external_hash(provider, payload["user_id"])
    request_row = _begin_deletion_request(provider, external_user_hash)
    code = request_row["confirmation_code"]

    affected = _disconnect_by_external_id(targets, payload["user_id"], delete_data=True, event=event)
    status = "completed" if affected or request_row.get("_previous_status") == "completed" else "not_found"
    _complete_deletion_request(code, status)
    log_action(event, f"provider={provider} status={status}")
    response = {"url": _status_url(code), "confirmation_code": code}
    _remember_replay(replay_key, response)
    return response


@router.post("/meta/deauthorize")
async def meta_deauthorize(request: Request):
    return await _handle_disconnect(
        request, secret=instagram_oauth.SECRET, targets=_META_TARGETS, event="meta_deauthorize"
    )


@router.post("/meta/data-deletion")
async def meta_data_deletion(request: Request):
    return await _handle_delete(
        request, secret=instagram_oauth.SECRET, targets=_META_TARGETS, provider="meta", event="meta_data_deletion"
    )


@router.get("/meta/data-deletion/status", name="data_deletion_status")
async def data_deletion_status(request: Request, code: str):
    _check_status_rate_limit(request)
    row = (
        supabase.table("data_deletion_requests")
        .select("confirmation_code, provider, status, created_at, completed_at")
        .eq("confirmation_code", code)
        .maybe_single()
        .execute()
    )
    if not row or not row.data:
        raise HTTPException(status_code=404, detail="Solicitacao nao encontrada")
    data = row.data
    return {
        "confirmation_code": data.get("confirmation_code"),
        "provider": data.get("provider"),
        "status": data.get("status"),
        "created_at": data.get("created_at"),
        "completed_at": data.get("completed_at"),
    }


@router.post("/threads/uninstall")
async def threads_uninstall(request: Request):
    return await _handle_disconnect(
        request, secret=threads_oauth.SECRET, targets=_THREADS_TARGETS, event="threads_uninstall"
    )


@router.post("/threads/delete")
async def threads_delete(request: Request):
    return await _handle_delete(
        request, secret=threads_oauth.SECRET, targets=_THREADS_TARGETS, provider="threads", event="threads_delete"
    )

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
from datetime import datetime, timezone
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request

from .. import instagram_oauth, threads_oauth
from ..audit_log import log_action
from ..audit_trail import record_audit_event
from ..config import settings
from ..database import supabase
from .auth import _check_login_rate_limit, client_ip

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["meta-callbacks"])

_MAX_BODY_BYTES = 4096

_META_TARGETS = (
    ("facebook", "facebook_credentials", "page_id"),
    ("instagram", "instagram_credentials", "ig_user_id"),
)
_THREADS_TARGETS = (("threads", "threads_credentials", "t_user_id"),)

_DEAUTHORIZE_UPDATES = {
    "facebook": {"page_access_token": None, "status": False},
    "instagram": {"user_access_token": None, "status": False},
    "threads": {"access_token": None, "status": False},
}
_DELETE_UPDATES = {
    "facebook": {"page_id": None, "page_name": None, "page_access_token": None, "status": False},
    "instagram": {"ig_user_id": None, "user_access_token": None, "status": False},
    "threads": {"t_user_id": None, "access_token": None, "status": False},
}


def _check_callback_rate_limit(request: Request) -> None:
    # ponytail: reusa o rate limit em memoria de auth.py; Redis se virar multi-worker.
    _check_login_rate_limit(
        f"meta-callback:{client_ip(request)}",
        detail="Muitas tentativas. Aguarde antes de tentar novamente.",
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

    expected = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="signed_request invalido")

    user_id = payload.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=400, detail="signed_request invalido")
    return {"user_id": user_id.strip()}


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
        raise HTTPException(status_code=400, detail="signed_request invalido")
    return _verify_signed_request(values[0], secret)


def _external_hash(provider: str, external_user_id: str) -> str:
    return hmac.new(
        settings.api_secret_key.encode("utf-8"),
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


def _disconnect_by_external_id(targets, external_user_id: str, *, delete_data: bool, event: str) -> int:
    affected = 0
    for network, table, id_column in targets:
        rows = (
            supabase.table(table)
            .select("id, user_id, profile_id")
            .eq(id_column, external_user_id)
            .execute()
            .data
            or []
        )
        if not rows:
            continue
        update_data = _DELETE_UPDATES[network] if delete_data else _DEAUTHORIZE_UPDATES[network]
        result = supabase.table(table).update(update_data).eq(id_column, external_user_id).execute()
        updated = result.data or rows
        affected += len(updated)
        _delete_credential_checks(rows, network)
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
    return affected


def _status_url(code: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/api/meta/data-deletion/status?code={code}"


def _existing_deletion_request(provider: str, external_user_hash: str) -> dict | None:
    row = (
        supabase.table("data_deletion_requests")
        .select("confirmation_code, status")
        .eq("provider", provider)
        .eq("external_user_hash", external_user_hash)
        .maybe_single()
        .execute()
    )
    return row.data if row and row.data else None


def _record_deletion_request(provider: str, external_user_hash: str, status: str) -> dict:
    existing = _existing_deletion_request(provider, external_user_hash)
    if existing:
        return existing
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "confirmation_code": secrets.token_urlsafe(24),
        "provider": provider,
        "external_user_hash": external_user_hash,
        "status": status,
        "completed_at": now,
    }
    result = supabase.table("data_deletion_requests").insert(row).execute()
    return result.data[0]


async def _handle_disconnect(request: Request, *, secret: str | None, targets, event: str) -> dict:
    _check_callback_rate_limit(request)
    payload = await _signed_payload(request, secret)
    affected = _disconnect_by_external_id(targets, payload["user_id"], delete_data=False, event=event)
    log_action(event, f"provider={event} matched={bool(affected)}")
    return {"status": "received"}


async def _handle_delete(request: Request, *, secret: str | None, targets, provider: str, event: str) -> dict:
    _check_callback_rate_limit(request)
    payload = await _signed_payload(request, secret)
    external_user_hash = _external_hash(provider, payload["user_id"])
    existing = _existing_deletion_request(provider, external_user_hash)
    if existing:
        code = existing["confirmation_code"]
        return {"url": _status_url(code), "confirmation_code": code}

    affected = _disconnect_by_external_id(targets, payload["user_id"], delete_data=True, event=event)
    status = "completed" if affected else "not_found"
    request_row = _record_deletion_request(provider, external_user_hash, status)
    log_action(event, f"provider={provider} status={status}")
    code = request_row["confirmation_code"]
    return {"url": _status_url(code), "confirmation_code": code}


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
async def data_deletion_status(code: str):
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

"""Conexão Shopee Vídeo de criadores afiliados, isolada da Affiliate GraphQL.

API oficial: https://open.shopee.com/developer-guide/706
Este módulo oferece configuração ADMIN, OAuth por perfil, status e prévia.
A publicação acontece pela fila durável de posts (rede "shopee_video",
scheduler/bot_post_shopee_video.py); tokens em api/shopee_video_tokens.py.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
from urllib.parse import urlsplit

from apis.shopee_video import (
    ShopeeVideoAuthorization, ShopeeVideoClient, ShopeeVideoError, ShopeeVideoRejected,
)
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from database.scheduler_environment import current_environment
from .. import shopee_video_oauth as oauth
from .. import shopee_video_tokens as tokens
from ..audit_log import log_action
from ..config import settings
from ..crypto import encrypt
from ..database import supabase
from ..profiles import scope_owner
from .auth import get_current_user_id
from .profiles import get_current_profile_id
from .credentials import _require_admin, _sign_oauth_state, _verify_oauth_state

router = APIRouter(tags=["shopee-video"])
logger = logging.getLogger("uvicorn.error")
APP_TABLE = tokens.APP_TABLE
USER_TABLE = tokens.USER_TABLE
OAUTH_COOKIE = "shopee_video_oauth_state"
PING_TIMEOUT_SECONDS = 20
MAX_DRAFT_BYTES = 50 * 1024 * 1024  # guarda conservadora do pipeline atual


class AppSettings(BaseModel):
    partner_id: int = Field(gt=0)
    partner_key: str = Field(min_length=8, max_length=1000)
    sandbox: bool = True


class VideoPreview(BaseModel):
    caption: str = Field(min_length=1, max_length=150)
    product_item_ids: list[int] = Field(min_length=1, max_length=6)
    video_seconds: int = Field(ge=3, le=60)
    video_bytes: int = Field(gt=0, le=MAX_DRAFT_BYTES)
    aigc_label: bool


def _config() -> dict:
    try:
        return tokens.app_config()
    except tokens.ShopeeVideoNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


def _callback_url() -> str:
    # O domínio é cadastrado na Shopee; nunca aceite URL de destino do cliente.
    url = (os.getenv("SHOPEE_VIDEO_CALLBACK_URL") or "").strip()
    if not url.startswith("https://") or not url.endswith("/api/shopee-video/callback"):
        raise HTTPException(status_code=503, detail="Callback Shopee Vídeo não configurado no servidor.")
    return url


def _profile(profile_id: str | None) -> str:
    if not profile_id:
        raise HTTPException(status_code=409, detail="Selecione um perfil antes de conectar a Shopee Vídeo.")
    return profile_id


@router.get("/admin/shopee-video")
async def admin_video_status(_admin: str = Depends(_require_admin)):
    row = tokens.app_row()
    return {
        "configured": tokens.is_configured(row),
        "partner_id": row.get("partner_id") if row else None,
        "sandbox": bool(row.get("sandbox")) if row else True,
        "callback_configured": bool((os.getenv("SHOPEE_VIDEO_CALLBACK_URL") or "").strip()),
    }


@router.put("/admin/shopee-video")
async def save_video_app(body: AppSettings, admin: str = Depends(_require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    data = {"partner_id": body.partner_id, "partner_key": encrypt(body.partner_key.strip()),
            "sandbox": body.sandbox, "enabled": True, "updated_at": now}
    result = supabase.table(APP_TABLE).upsert(
        {"environment": current_environment(), **data}, on_conflict="environment",
    ).execute()
    if not result.data:
        raise HTTPException(status_code=503, detail="Não foi possível salvar a configuração Shopee Vídeo.")
    log_action("shopee_video_app_configured", "shopee-video", user_id=admin)
    return {"configured": True, "sandbox": body.sandbox}


@router.get("/shopee-video/status")
async def video_status(
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """{configured, connected, token_valid, needs_reconnect, sandbox, publishing_enabled}."""
    return tokens.connection_state(user_id, profile_id)


@router.get("/shopee-video/authorize")
async def video_authorize(
    response: Response,
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    _profile(profile_id)
    config = _config()
    callback = _callback_url()
    state, cookie = _sign_oauth_state(user_id, profile_id=profile_id,
                                      extra={"video_partner_id": config["partner_id"]})
    response.set_cookie(OAUTH_COOKIE, cookie, httponly=True, secure=True,
                        samesite="lax", max_age=600, path="/")
    log_action("shopee_video_oauth_authorize", user_id=user_id, profile_id=profile_id)
    return {"url": oauth.authorization_url(config["partner_id"], callback, state,
                                           sandbox=config["sandbox"])}


@router.get("/shopee-video/callback")
async def video_callback(
    request: Request, code: str | None = None, state: str | None = None,
    error: str | None = None,
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    def redirect(outcome: str) -> RedirectResponse:
        target = f"{settings.frontend_url.rstrip('/')}/credentials?shopee_video={outcome}"
        response = RedirectResponse(target, status_code=303)
        response.delete_cookie(OAUTH_COOKIE, path="/")
        return response

    if error or not code or not profile_id:
        return redirect("error")
    state_payload = _verify_oauth_state(request, OAUTH_COOKIE, state, user_id, profile_id)
    if not state_payload:
        return redirect("error")
    try:
        config = _config()
        if config["partner_id"] != state_payload.get("video_partner_id"):
            return redirect("error")
        result = await oauth.exchange_code(config["partner_id"], config["partner_key"],
                                           code, sandbox=config["sandbox"])
        now = datetime.now(timezone.utc)
        # Reconectar zera needs_reconnect/reconnect_reason (token_columns).
        saved = supabase.table(USER_TABLE).upsert({
            "environment": current_environment(), "user_id": user_id, "profile_id": profile_id,
            "partner_id": config["partner_id"], "shopee_user_id": result["user_id_list"][0],
            **tokens.token_columns(result, now),
        }, on_conflict="environment,user_id,profile_id").execute()
        if not saved.data:
            raise RuntimeError("Persistência indisponível")
    except (oauth.ShopeeVideoOAuthError, HTTPException, RuntimeError, ValueError, KeyError):
        logger.warning("OAuth Shopee Vídeo não concluído para o perfil atual")
        return redirect("error")
    log_action("shopee_video_oauth_connected", user_id=user_id, profile_id=profile_id)
    return redirect("success")


@router.post("/shopee-video/refresh")
async def refresh_video_authorization(
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Renova apenas a autorização do perfil ativo, sem expor tokens."""
    profile = _profile(profile_id)
    config = _config()
    row = await asyncio.to_thread(tokens.auth_row, user_id, profile)
    valid_until = tokens.parse_datetime(row.get("refresh_expires_at")) if row else None
    if (not row or row.get("partner_id") != config["partner_id"] or row.get("needs_reconnect")
            or not valid_until or valid_until <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=409, detail="Reconecte a conta Shopee Vídeo para continuar.")
    try:
        await asyncio.to_thread(
            tokens.refresh_authorization, user_id, profile, config, row, datetime.now(timezone.utc),
        )
    except tokens.ShopeeVideoReconnectRequired:
        raise HTTPException(status_code=409, detail=tokens.RECONNECT_MESSAGE) from None
    except (oauth.ShopeeVideoOAuthError, ValueError, KeyError):
        logger.warning("Não foi possível renovar OAuth Shopee Vídeo para o perfil atual")
        raise HTTPException(status_code=503, detail="Falha ao renovar o acesso à Shopee Vídeo.") from None
    log_action("shopee_video_oauth_refreshed", user_id=user_id, profile_id=profile)
    return {"connected": True, "token_valid": True}


def _ping_video_list(auth: tokens.ValidAuthorization) -> dict:
    """get_video_list(1, 1): somente leitura. Síncrono; rode em thread."""
    client = ShopeeVideoClient(
        ShopeeVideoAuthorization(auth.partner_id, auth.partner_key, auth.shopee_user_id,
                                 auth.access_token, permission_granted=True),
        sandbox=auth.sandbox, enabled=True,
    )
    data = client.get_video_list(page_no=1, page_size=1)
    videos = data.get("video_list")
    return {
        "ok": True, "http_reachable": True,
        "videos_returned": len(videos) if isinstance(videos, list) else 0,
        "response_keys": sorted(str(key) for key in data),
        "sandbox": auth.sandbox,
        "host": urlsplit(client.host).hostname or "",
    }


@router.post("/shopee-video/test-connection")
async def test_video_connection(
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Ping somente leitura (v2.video.get_video_list). Não publica nem devolve segredos."""
    profile = _profile(profile_id)
    try:
        auth = await asyncio.to_thread(tokens.get_valid_authorization, user_id, profile)
    except tokens.ShopeeVideoReconnectRequired:
        raise HTTPException(status_code=409, detail=tokens.RECONNECT_MESSAGE) from None
    except tokens.ShopeeVideoNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except (oauth.ShopeeVideoOAuthError, ValueError, KeyError):
        logger.warning("Autorização Shopee Vídeo indisponível no teste de conexão")
        raise HTTPException(status_code=503, detail="Falha ao renovar o acesso à Shopee Vídeo.") from None
    try:
        result = await asyncio.wait_for(asyncio.to_thread(_ping_video_list, auth), PING_TIMEOUT_SECONDS)
    except ShopeeVideoRejected as exc:
        result = {"ok": False, "http_reachable": True, "shopee_error": exc.code,
                  "shopee_message": exc.detail[:200], "request_id": exc.request_id}
    except (ShopeeVideoError, asyncio.TimeoutError):
        result = {"ok": False, "http_reachable": False, "error": "Falha de comunicação com a Shopee"}
    log_action("shopee_video_test_connection", f"ok={result['ok']}", user_id=user_id, profile_id=profile)
    return result


@router.delete("/shopee-video/authorization")
async def disconnect_video(
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile = _profile(profile_id)
    scope_owner(supabase.table(USER_TABLE).delete(), user_id, profile).eq(
        "environment", current_environment(),
    ).execute()
    log_action("shopee_video_oauth_disconnected", user_id=user_id, profile_id=profile)
    return {"connected": False}


@router.post("/shopee-video/preview")
async def preview_video(
    body: VideoPreview,
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Teste local seguro: não envia arquivo ou publica na Shopee."""
    profile = _profile(profile_id)
    if not body.caption.strip() or len(set(body.product_item_ids)) != len(body.product_item_ids):
        raise HTTPException(status_code=422, detail="Revise a legenda e os produtos duplicados.")
    if any(item <= 0 for item in body.product_item_ids):
        raise HTTPException(status_code=422, detail="ID de produto inválido.")
    selected = scope_owner(
        supabase.table("products").select("product_id"), user_id, profile,
    ).in_("product_id", body.product_item_ids).execute()
    owned = {int(row["product_id"]) for row in (selected.data or [])}
    if owned != set(body.product_item_ids):
        raise HTTPException(status_code=422, detail="Selecione apenas produtos cadastrados neste perfil.")
    return {
        "valid": True, "product_count": len(owned), "caption_length": len(body.caption),
        "duration_seconds": body.video_seconds, "aigc_label": body.aigc_label,
        "publication": "não enviada", "message": "Prévia válida; nenhum vídeo foi publicado.",
    }

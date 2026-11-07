"""Conexão Shopee Vídeo de criadores afiliados, isolada da Affiliate GraphQL.

API oficial: https://open.shopee.com/developer-guide/706
Este módulo oferece configuração ADMIN, OAuth por perfil e validação de prévia.
Não publica nem cria jobs; a liberação de postagem exige fila durável própria.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from database.scheduler_environment import current_environment
from .. import shopee_video_oauth as oauth
from ..audit_log import log_action
from ..config import settings
from ..crypto import encrypt, decrypt
from ..database import supabase
from ..profiles import scope_owner
from .auth import get_current_user_id
from .profiles import get_current_profile_id
from .credentials import _require_admin, _sign_oauth_state, _verify_oauth_state

router = APIRouter(tags=["shopee-video"])
logger = logging.getLogger("uvicorn.error")
APP_TABLE = "platform_shopee_video_apps"
USER_TABLE = "shopee_video_authorizations"
OAUTH_COOKIE = "shopee_video_oauth_state"
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


def _config_row() -> dict | None:
    result = supabase.table(APP_TABLE).select(
        "partner_id,partner_key,sandbox,enabled"
    ).eq("environment", current_environment()).maybe_single().execute()
    return result.data if result else None


def _config() -> dict:
    row = _config_row()
    if not row or not row.get("enabled") or not row.get("partner_id") or not row.get("partner_key"):
        raise HTTPException(status_code=503, detail="Shopee Vídeo ainda não está configurada pelo administrador.")
    try:
        return {"partner_id": int(row["partner_id"]), "partner_key": decrypt(row["partner_key"]),
                "sandbox": bool(row["sandbox"])}
    except Exception:
        logger.error("Erro ao decifrar chave global Shopee Vídeo")
        raise HTTPException(status_code=503, detail="Configuração de Shopee Vídeo indisponível.") from None


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


def _own_auth(user_id: str, profile_id: str) -> dict | None:
    result = scope_owner(
        supabase.table(USER_TABLE).select(
            "partner_id,shopee_user_id,access_token,refresh_token,expires_at,refresh_expires_at"
        ), user_id, profile_id,
    ).eq("environment", current_environment()).maybe_single().execute()
    return result.data if result else None


def _expiry(token_data: dict) -> datetime:
    """Algumas respostas usam duração, outras timestamp absoluto de segundos."""
    now = datetime.now(timezone.utc)
    raw = token_data.get("expire_in", 14400)
    try:
        value = int(raw)
    except (ValueError, TypeError):
        value = 14400
    if value > 1_000_000_000:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return now + timedelta(seconds=max(60, min(value, 14400)))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


@router.get("/admin/shopee-video")
async def admin_video_status(_admin: str = Depends(_require_admin)):
    row = _config_row()
    return {
        "configured": bool(row and row.get("enabled") and row.get("partner_key")),
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
    config = _config_row()
    ready = bool(config and config.get("enabled") and config.get("partner_key"))
    row = _own_auth(user_id, profile_id) if profile_id else None
    match = bool(row and ready and row.get("partner_id") == config.get("partner_id"))
    expiry = _parse_datetime(row.get("expires_at")) if match else None
    refresh_expiry = _parse_datetime(row.get("refresh_expires_at")) if match else None
    valid = bool(match and row.get("access_token") and expiry and expiry > datetime.now(timezone.utc))
    return {
        "configured": ready,
        "connected": bool(match and row.get("refresh_token") and refresh_expiry
                          and refresh_expiry > datetime.now(timezone.utc)),
        "token_valid": valid,
        "sandbox": bool(config.get("sandbox")) if ready else None,
        "publishing_enabled": False,  # nenhum publicador ativo nesta fase
    }


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
        saved = supabase.table(USER_TABLE).upsert({
            "environment": current_environment(), "user_id": user_id, "profile_id": profile_id,
            "partner_id": config["partner_id"], "shopee_user_id": result["user_id_list"][0],
            "access_token": encrypt(result["access_token"]),
            "refresh_token": encrypt(result["refresh_token"]),
            "expires_at": _expiry(result).isoformat(),
            "refresh_expires_at": (now + timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat(),
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
    row = _own_auth(user_id, profile)
    valid_until = _parse_datetime(row.get("refresh_expires_at")) if row else None
    if (not row or row.get("partner_id") != config["partner_id"]
            or not valid_until or valid_until <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=409, detail="Reconecte a conta Shopee Vídeo para continuar.")
    try:
        result = await oauth.refresh_token(
            config["partner_id"], config["partner_key"], int(row["shopee_user_id"]),
            decrypt(row["refresh_token"]), sandbox=config["sandbox"],
        )
        now = datetime.now(timezone.utc)
        renewed = scope_owner(supabase.table(USER_TABLE).update({
            "access_token": encrypt(result["access_token"]),
            "refresh_token": encrypt(result["refresh_token"]),
            "expires_at": _expiry(result).isoformat(),
            "refresh_expires_at": (now + timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat(),
        }), user_id, profile).eq("environment", current_environment()).eq(
            "partner_id", config["partner_id"],
        ).eq("shopee_user_id", row["shopee_user_id"]).execute()
        if not renewed.data:
            raise RuntimeError("Autorização não encontrada para renovação")
    except (oauth.ShopeeVideoOAuthError, RuntimeError, ValueError, KeyError):
        logger.warning("Não foi possível renovar OAuth Shopee Vídeo para o perfil atual")
        raise HTTPException(status_code=503, detail="Falha ao renovar o acesso à Shopee Vídeo.") from None
    log_action("shopee_video_oauth_refreshed", user_id=user_id, profile_id=profile)
    return {"connected": True, "token_valid": True}


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

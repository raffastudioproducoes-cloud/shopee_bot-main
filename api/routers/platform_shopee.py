"""Shopee: catálogo com chave da plataforma, ID de afiliado por conta.

Nenhuma rota USER retorna App ID ou Secret global. `affiliate_id` identifica a
atribuição desejada, mas não representa OAuth nem comprova titularidade.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database.scheduler_environment import current_environment
from ..audit_log import log_action
from ..crypto import decrypt, encrypt
from ..database import supabase
from ..profiles import scope_account
from ..shopee_affiliate_links import affiliate_id_from_link
from ..internal_client import validate_shopee_credential
from .auth import get_current_user_id
from .credentials import _check_test_rate_limit, _require_admin

logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=["platform-shopee"])
TABLE = "platform_shopee_credentials"
AFFILIATE_TABLE = "shopee_affiliate_accounts"
UNAVAILABLE = "Catálogo Shopee temporariamente indisponível. Tente mais tarde."


class PlatformShopeeBody(BaseModel):
    app_id: str
    secret: str


class AffiliateIdentityBody(BaseModel):
    affiliate_id: str


def _platform_row() -> dict | None:
    result = supabase.table(TABLE).select(
        "app_id, secret, status, check_state, checked_at"
    ).eq("environment", current_environment()).maybe_single().execute()
    return result.data if result else None


def resolve_platform_shopee_key() -> tuple[str, str]:
    """Somente backend — o segredo nunca entra no payload de catálogo."""
    row = _platform_row()
    if not row or not row.get("status") or not row.get("app_id") or not row.get("secret"):
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    try:
        return row["app_id"], decrypt(row["secret"])
    except Exception:
        logger.error("Credencial Shopee global não pôde ser decifrada")
        raise HTTPException(status_code=503, detail=UNAVAILABLE) from None


def get_affiliate_id(user_id: int) -> str | None:
    row = scope_account(
        supabase.table(AFFILIATE_TABLE).select("affiliate_id"), user_id,
    ).maybe_single().execute()
    return (row.data or {}).get("affiliate_id") if row else None


@router.get("/shopee/affiliate")
async def affiliate_status(user_id: int = Depends(get_current_user_id)):
    affiliate_id = get_affiliate_id(user_id)
    row = _platform_row()
    return {
        "connected": bool(affiliate_id), "affiliate_id": affiliate_id,
        "catalog_available": bool(row and row.get("status") and row.get("app_id") and row.get("secret")),
    }


@router.put("/shopee/affiliate")
async def save_affiliate_identity(
    body: AffiliateIdentityBody, user_id: int = Depends(get_current_user_id),
):
    affiliate_id = affiliate_id_from_link(body.affiliate_id)
    if affiliate_id is None:
        raise HTTPException(status_code=400, detail=(
            "Informe seu ID numérico de afiliado Shopee ou um link completo com o identificador. "
            "Links curtos precisam ser expandidos no navegador antes de colar."
        ))
    now = datetime.now(timezone.utc).isoformat()
    row = scope_account(supabase.table(AFFILIATE_TABLE).select("user_id"), user_id).maybe_single().execute()
    if row and row.data:
        saved = scope_account(supabase.table(AFFILIATE_TABLE).update({
            "affiliate_id": affiliate_id, "updated_at": now,
        }), user_id).execute()
    else:
        saved = supabase.table(AFFILIATE_TABLE).insert({
            "user_id": user_id, "affiliate_id": affiliate_id, "updated_at": now,
        }).execute()
    if not saved.data:
        raise HTTPException(status_code=503, detail="Não foi possível salvar o ID de afiliado.")
    log_action("shopee_affiliate_id_saved", "shopee", user_id=user_id)
    return {"connected": True, "affiliate_id": affiliate_id}


@router.delete("/shopee/affiliate")
async def remove_affiliate_identity(user_id: int = Depends(get_current_user_id)):
    scope_account(supabase.table(AFFILIATE_TABLE).delete(), user_id).execute()
    log_action("shopee_affiliate_id_removed", "shopee", user_id=user_id)
    return {"connected": False, "affiliate_id": None}


@router.get("/admin/shopee")
async def admin_shopee_status(_admin: int = Depends(_require_admin)):
    row = _platform_row()
    connected = bool(row and row.get("status") and row.get("app_id") and row.get("secret"))
    return {
        "connected": connected,
        "state": row.get("check_state") if connected and row else None,
        "checked_at": row.get("checked_at") if row else None,
    }


@router.put("/admin/shopee")
async def save_platform_shopee(
    body: PlatformShopeeBody, admin: int = Depends(_require_admin),
):
    app_id, secret = body.app_id.strip(), body.secret.strip()
    if not app_id or len(app_id) > 200 or not secret or len(secret) > 1000:
        raise HTTPException(status_code=400, detail="Informe App ID e Secret válidos.")
    now = datetime.now(timezone.utc).isoformat()
    data = {"app_id": app_id, "secret": encrypt(secret), "status": True,
            "check_state": None, "check_message": None, "checked_at": None,
            "updated_at": now}
    if _platform_row():
        result = supabase.table(TABLE).update(data).eq(
            "environment", current_environment(),
        ).execute()
    else:
        result = supabase.table(TABLE).insert({
            "environment": current_environment(), **data,
        }).execute()
    if not result.data:
        raise HTTPException(status_code=503, detail="Não foi possível salvar as credenciais Shopee.")
    log_action("platform_shopee_saved", "shopee", user_id=admin)
    return {"connected": True}


@router.delete("/admin/shopee")
async def remove_platform_shopee(admin: int = Depends(_require_admin)):
    result = supabase.table(TABLE).update({
        "app_id": None, "secret": None, "status": False,
        "check_state": None, "check_message": None, "checked_at": None,
    }).eq("environment", current_environment()).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Credenciais globais não configuradas.")
    log_action("platform_shopee_removed", "shopee", user_id=admin)
    return {"connected": False}


@router.post("/admin/shopee/test")
async def test_platform_shopee(admin: int = Depends(_require_admin)):
    _check_test_rate_limit(admin)
    return await _execute_platform_shopee_test(admin)


async def _execute_platform_shopee_test(admin: int) -> dict:
    """Verifica a API global sem duplicar o limite do diagnóstico agregado."""
    app_id, secret = resolve_platform_shopee_key()
    try:
        ok = await validate_shopee_credential(app_id, secret)
        state, message = ("ok", "API de afiliados respondeu corretamente") if ok else (
            "error", "A Shopee não validou as credenciais da plataforma")
    except Exception as exc:
        logger.warning("Falha no teste de API Shopee (%s)", type(exc).__name__)
        state, message = "error", "Não foi possível verificar a API Shopee agora"
    now = datetime.now(timezone.utc).isoformat()
    supabase.table(TABLE).update({
        "check_state": state, "check_message": message, "checked_at": now,
    }).eq("environment", current_environment()).execute()
    log_action("platform_shopee_tested", "shopee", user_id=admin)
    return {"light": "green" if state == "ok" else "red",
            "message": message, "checked_at": now}

"""Serviço de IA da plataforma: segredo global, operações administrativas isoladas.

Nenhuma rota pública recebe ou devolve uma chave. A configuração pertence ao
Auto Orbital, nunca ao perfil/conta que pede a geração de texto.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from apis import llm
from database.scheduler_environment import current_environment
from ..audit_log import log_action
from ..crypto import decrypt, encrypt
from ..database import supabase
from .auth import get_current_user_id
from .credentials import (
    _autotest_submit, _call_with_timeout, _check_test_rate_limit,
    _connection_state, _parse_ts, _require_admin, _status_only,
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=["platform-ai"])

KEYS_TABLE = "platform_ai_credentials"
SETTINGS_TABLE = "platform_ai_settings"
KEY_MAX_LEN = 500
UNAVAILABLE = "Serviço de IA temporariamente indisponível. Tente novamente mais tarde."


class PlatformAiCredentialBody(BaseModel):
    api_key: str
    model: str | None = None


def _provider(provider: str) -> str:
    if provider not in llm.PROVIDERS:
        raise HTTPException(status_code=404, detail="Provedor de IA não suportado")
    return provider


def _settings() -> dict:
    row = supabase.table(SETTINGS_TABLE).select("active_provider").eq(
        "environment", current_environment()
    ).maybe_single().execute()
    if not row or not row.data:
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    return row.data


def _rows() -> list[dict]:
    return supabase.table(KEYS_TABLE).select(
        "provider, secret, model, status, updated_at, check_state, check_message, checked_at"
    ).eq("environment", current_environment()).execute().data or []


def _key_for_provider(provider: str) -> tuple[str, str | None]:
    row = supabase.table(KEYS_TABLE).select("secret, model, status").eq(
        "provider", _provider(provider)
    ).eq("environment", current_environment()).maybe_single().execute()
    data = row.data if row else None
    if not data or not data.get("status") or not data.get("secret"):
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    try:
        return decrypt(data["secret"]), data.get("model")
    except Exception:
        logger.error("Chave de IA da plataforma não pôde ser decifrada")
        raise HTTPException(status_code=503, detail=UNAVAILABLE) from None


def resolve_platform_ai_key() -> tuple[str, str, str | None]:
    """Credencial ativa da plataforma (sem argumento de usuário ou provedor do cliente)."""
    provider = _settings().get("active_provider")
    if provider not in llm.PROVIDERS:
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    api_key, model = _key_for_provider(provider)
    return provider, api_key, model


def _available() -> bool:
    provider = _settings().get("active_provider")
    if provider not in llm.PROVIDERS:
        return False
    row = supabase.table(KEYS_TABLE).select("secret, status").eq(
        "provider", provider
    ).eq("environment", current_environment()).maybe_single().execute()
    return bool(row and row.data and row.data.get("status") and row.data.get("secret"))


@router.get("/ai/status")
async def platform_ai_status(_user_id: int = Depends(get_current_user_id)):
    """Somente disponibilidade; nunca revela provedor, chave, modelo ou testes."""
    return {"available": _available()}


@router.get("/admin/ai")
async def admin_platform_ai_status(_admin: int = Depends(_require_admin)):
    rows = {row["provider"]: row for row in _rows()}
    active = _settings().get("active_provider")
    providers = {}
    for provider in llm.PROVIDERS:
        row = rows.get(provider)
        connected = bool(row and row.get("status") and row.get("secret"))
        check = ({"state": row.get("check_state"), "message": row.get("check_message"),
                  "checked_at": row.get("checked_at")}) if row and row.get("check_state") else None
        state = _status_only({"status": connected}, check)
        providers[provider] = {**state, "model": row.get("model") if row else None,
                               "default_model": llm.DEFAULT_MODELS[provider]}
    return {"providers": providers, "active": active if active in llm.PROVIDERS else None}


def _mark_check(provider: str, state: str, message: str = "") -> str:
    checked_at = datetime.now(timezone.utc).isoformat()
    supabase.table(KEYS_TABLE).update({
        "check_state": state, "check_message": message, "checked_at": checked_at,
    }).eq("provider", provider).eq("environment", current_environment()).execute()
    return checked_at


def _run_autotest(provider: str, started_at: str) -> None:
    try:
        api_key, model = _key_for_provider(provider)
        _call_with_timeout(llm.check_key, provider, api_key, model)
        state, message = "ok", "Chave funcionando"
    except llm.LLMError as exc:
        state, message = "error", str(exc)
    except Exception as exc:
        logger.warning("Falha no teste automático da IA (%s): %s", provider, type(exc).__name__)
        state, message = "error", "Não foi possível testar a conexão agora"
    try:
        row = supabase.table(KEYS_TABLE).select("check_state, checked_at, status").eq(
            "provider", provider
        ).eq("environment", current_environment()).maybe_single().execute()
        current = row.data if row else None
        if not current or not current.get("status") or current.get("check_state") != "testing":
            return
        if _parse_ts(current.get("checked_at")) != _parse_ts(started_at):
            return  # outra gravação/desconexão/teste mais recente venceu
        _mark_check(provider, state, message)
    except Exception as exc:
        logger.warning("Não foi possível registrar teste automático da IA (%s): %s", provider, type(exc).__name__)


@router.put("/admin/ai/{provider}")
async def save_platform_ai_key(
    provider: str, body: PlatformAiCredentialBody, admin: int = Depends(_require_admin),
):
    provider = _provider(provider)
    api_key = body.api_key.strip()
    model = (body.model or "").strip() or None
    if not api_key or len(api_key) > KEY_MAX_LEN:
        raise HTTPException(status_code=400, detail="Informe uma chave de API válida.")
    if model and not llm.valid_model(model):
        raise HTTPException(status_code=400, detail="Nome de modelo inválido.")

    data = {"secret": encrypt(api_key), "model": model, "status": True,
            "updated_at": datetime.now(timezone.utc).isoformat(), "check_state": "testing",
            "check_message": "", "checked_at": datetime.now(timezone.utc).isoformat()}
    row = supabase.table(KEYS_TABLE).select("provider").eq(
        "provider", provider
    ).eq("environment", current_environment()).maybe_single().execute()
    if row and row.data:
        saved = supabase.table(KEYS_TABLE).update(data).eq(
            "provider", provider
        ).eq("environment", current_environment()).execute()
    else:
        saved = supabase.table(KEYS_TABLE).insert({
            "environment": current_environment(), "provider": provider, **data,
        }).execute()
    if not saved.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar credencial de IA")
    activated = supabase.table(SETTINGS_TABLE).update({
        "active_provider": provider, "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("environment", current_environment()).execute()
    if not activated.data:
        raise HTTPException(status_code=503, detail="Falha ao ativar provedor de IA")
    try:
        _autotest_submit(_run_autotest, provider, data["checked_at"])
    except Exception as exc:
        logger.warning("Teste automático da IA não iniciado: %s", type(exc).__name__)
    log_action("platform_ai_key_saved", provider, user_id=admin)
    return {"connected": True}


@router.post("/admin/ai/{provider}/activate")
async def activate_platform_ai_provider(provider: str, admin: int = Depends(_require_admin)):
    provider = _provider(provider)
    _key_for_provider(provider)
    result = supabase.table(SETTINGS_TABLE).update({
        "active_provider": provider, "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("environment", current_environment()).execute()
    if not result.data:
        raise HTTPException(status_code=503, detail="Falha ao ativar provedor de IA")
    log_action("platform_ai_provider_activated", provider, user_id=admin)
    return {"active": provider}


@router.delete("/admin/ai/{provider}")
async def delete_platform_ai_key(provider: str, admin: int = Depends(_require_admin)):
    provider = _provider(provider)
    row = supabase.table(KEYS_TABLE).update({
        "secret": None, "status": False, "check_state": None,
        "check_message": None, "checked_at": None,
    }).eq("provider", provider).eq("environment", current_environment()).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Credencial de IA não encontrada")
    if _settings().get("active_provider") == provider:
        supabase.table(SETTINGS_TABLE).update({"active_provider": None}).eq(
            "environment", current_environment()
        ).execute()
    log_action("platform_ai_key_deleted", provider, user_id=admin)
    return {"connected": False}


@router.post("/admin/ai/{provider}/test")
async def test_platform_ai_key(provider: str, admin: int = Depends(_require_admin)):
    provider = _provider(provider)
    _check_test_rate_limit(admin)
    api_key, model = _key_for_provider(provider)
    try:
        await run_in_threadpool(llm.check_key, provider, api_key, model)
        state, message = "ok", "Chave funcionando"
    except llm.LLMError as exc:
        state, message = "error", str(exc)
    checked_at = _mark_check(provider, state, message)
    light, connection_state, status_text = _connection_state(True, {
        "state": state, "message": message, "checked_at": checked_at,
    })
    log_action("platform_ai_key_tested", provider, user_id=admin)
    return {"light": light, "state": connection_state, "status_text": status_text,
            "message": message, "checked_at": checked_at}

"""Área administrativa: mesmos handlers, com autorização também no prefixo."""
import asyncio
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from ..admin_metrics import AdminMetricsResponse, collect_admin_metrics
from ..database import supabase
from ..config import settings
from .auth import get_current_user_id
from ..admin_operations import OperationsResponse, collect_operations
from ..admin_queue_health import QueueHealthResponse, collect_queue_health
from ..admin_views import AdminLogsResponse, AdminCredentialStatus
from ..audit_log import log_action
from .. import plan_grants
from ..rate_limiter import check_window
from .profiles import get_current_profile_id

from . import logs, users, credentials, platform_ai, platform_shopee

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(users._require_admin)])
router.add_api_route("/users", users.list_users, methods=["GET"])
router.add_api_route("/users", users.create_user, methods=["POST"], status_code=201)
router.add_api_route("/users/{user_id}", users.get_user, methods=["GET"])
router.add_api_route("/users/{user_id}", users.update_user, methods=["PUT"])
router.add_api_route("/users/{user_id}", users.delete_user, methods=["DELETE"])
router.add_api_route("/users/{user_id}/erasure/retry", users.resume_erasure, methods=["POST"])

_PLAN_RATE_ATTEMPTS = 30
_plan_attempts: dict = {}


@router.put("/users/{user_id}/plan")
async def set_user_plan(user_id: str, body: plan_grants.PlanGrantRequest,
                        admin_id: str = Depends(get_current_user_id)):
    """Concede Pro/Premium por prazo (1 a 365 dias) ou remove o plano ("free"). Só ADMIN."""
    check_window("admin-plan-grant", admin_id, attempts=_PLAN_RATE_ATTEMPTS, window_seconds=60,
                 state=_plan_attempts, detail="Muitas alterações de plano em pouco tempo. Aguarde um minuto.")
    return await run_in_threadpool(plan_grants.apply_plan, admin_id, user_id, body)
# Overrides manuais de credenciais (token já emitido): só ADMIN, reutilizando
# os handlers de credentials (sem rota equivalente em /credentials).
router.add_api_route("/credentials/threads", credentials.save_threads_credential, methods=["PUT"])
for _network, _handler in (
    ("x", credentials.save_x_credential_manual),
    ("facebook", credentials.save_facebook_credential_manual),
    ("tiktok", credentials.save_tiktok_credential_manual),
    ("instagram", credentials.save_instagram_credential_manual),
    ("kwai", credentials.save_kwai_credential_manual),
):
    router.add_api_route(f"/credentials/{_network}/manual", _handler, methods=["PUT"])
router.add_api_route("/logs", logs.list_logs, methods=["GET"], response_model=AdminLogsResponse)


@router.get('/credentials/status', response_model=dict[str, AdminCredentialStatus])
async def connection_status(statuses: dict = Depends(credentials.list_credentials)):
    return statuses


@router.post("/credentials/test-all")
async def test_all_connections(
    admin: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Uma tentativa administrativa para o lote; sem testar IDs de afiliado como chaves.

    Não acessa dados de outros clientes: redes OAuth são as credenciais do
    perfil ADMIN atual. Somente IA ativa e Shopee global são compartilhadas.
    """
    credentials._check_test_rate_limit(admin)
    statuses = await credentials.list_credentials(admin, profile_id)
    shopee_status = await platform_shopee.admin_shopee_status()
    try:
        ai_status = await platform_ai.admin_platform_ai_status()
    except Exception as exc:
        logger.warning("Diagnóstico: configuração de IA indisponível (%s)", type(exc).__name__)
        ai_status = {"active": None, "providers": {}}

    runners = {}
    active_ai = ai_status.get("active")
    if active_ai and ai_status.get("providers", {}).get(active_ai, {}).get("connected"):
        runners["ai"] = lambda: platform_ai._execute_platform_ai_test(active_ai, admin)
    if shopee_status.get("connected"):
        runners["shopee"] = lambda: platform_shopee._execute_platform_shopee_test(admin)

    # A API antiga associa "shopee" ao ID de afiliado do ADMIN; a conexão
    # global Shopee é a única testável aqui. Kwai permanece diagnóstico apenas.
    for network in ("facebook", "instagram", "kwai", "threads", "tiktok", "x"):
        if statuses.get(network, {}).get("connected"):
            runners[network] = lambda network=network: credentials._execute_credential_test(
                network, admin, profile_id
            )

    semaphore = asyncio.Semaphore(3)

    async def run_one(network, operation):
        async with semaphore:
            try:
                result = await operation()
                state = "ok" if result.get("light") == "green" else "error"
                checked_at = result.get("checked_at")
            except Exception as exc:
                logger.warning("Diagnóstico ADMIN: teste %s indisponível (%s)", network, type(exc).__name__)
                state, checked_at = "error", None
            # Nunca salvar erros crus de fornecedor (podem incluir IDs/chaves).
            # Render recebe evento sempre. Esta ação ADMIN explícita exige
            # auditoria, mesmo sem logging geral de tráfego. Nenhum segredo.
            logger.info("credential_diagnostic network=%s state=%s", network, state)
            log_action(f"admin_credentials_test_{network}_{state}", user_id=admin, force=True)
            return network, {"state": state, "status_text": (
                "Funcionando" if state == "ok" else "Falha no teste de conexão"
            ), "checked_at": checked_at}

    completed = dict(await asyncio.gather(*(run_one(name, fn) for name, fn in runners.items())))
    results = {}
    for key in ("ai", "shopee", "facebook", "instagram", "kwai", "threads", "tiktok", "x"):
        results[key] = completed.get(key, {
            "state": "skipped", "status_text": "Não configurada — teste não executado", "checked_at": None,
        })
    log_action("admin_credentials_test_all", f"tested={len(completed)} skipped={8-len(completed)}", user_id=admin, force=True)
    logger.info("credential_diagnostic_batch tested=%s skipped=%s", len(completed), 8 - len(completed))
    return {"tested": len(completed), "skipped": 8 - len(completed), "results": results}


@router.get("/metrics", response_model=AdminMetricsResponse)
async def metrics(days: int = Query(30, ge=7, le=90)):
    return await collect_admin_metrics(days)


@router.get("/queue-health", response_model=QueueHealthResponse)
async def queue_health():
    """Global, aggregate-only publication queue health; ADMIN dependency on router."""
    return await collect_queue_health()


@router.get("/operations", response_model=OperationsResponse)
async def operations():
    return await collect_operations()


@router.get("/my-region", response_model=dict[str, str | None])
async def my_region(user_id: str = Depends(get_current_user_id)):
    """Only the logged-in admin's voluntary region; never identifies another user.

    This endpoint does not change the k>=3 threshold for all-client aggregates.
    """
    result = (
        supabase.table("account_region_preferences")
        .select("region")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    own = (result.data or [None])[0]
    return {"region": own["region"] if own else None}


class ClientGeoPoint(BaseModel):
    account: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: int | None = None
    collected_at: datetime


class ClientGeoOverview(BaseModel):
    status: str
    updated_at: datetime
    customers_total: int = Field(ge=0)
    recent_active: int = Field(ge=0)
    activity_available: bool
    gps_points_total: int = Field(ge=0)
    region_participants: int = Field(ge=0)
    deleted_total: int = Field(ge=0)
    deleted_since: date | None
    points: list[ClientGeoPoint] = Field(max_length=500)


@router.get("/location-points", response_model=ClientGeoOverview)
async def location_points():
    """Somente clientes USER. Totais reais (0 ou 1 inclusive); pontos autorizados.

    A RPC faz a junção com users.access e limita a amostra cartográfica a 500.
    O histórico de exclusões vem de contadores diários sem IDs pessoais.
    """
    result = supabase.rpc("admin_client_geo_overview").execute()
    return {**result.data, "activity_available": settings.request_logging_enabled}


@router.get("/my-location")
async def my_location(user_id: str = Depends(get_current_user_id)):
    """O GPS próprio do administrador é separado dos pontos comerciais."""
    result = (
        supabase.table("account_location_sharing")
        .select("latitude,longitude,collected_at")
        .eq("user_id", user_id)
        .eq("choice", "accepted")
        .limit(1)
        .execute()
    )
    point = (result.data or [None])[0]
    return {"point": point}

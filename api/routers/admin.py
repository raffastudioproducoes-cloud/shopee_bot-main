"""Área administrativa: mesmos handlers, com autorização também no prefixo."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..admin_metrics import AdminMetricsResponse, collect_admin_metrics
from ..database import supabase
from ..config import settings
from .auth import get_current_user_id
from ..admin_operations import OperationsResponse, collect_operations
from ..admin_queue_health import QueueHealthResponse, collect_queue_health
from ..admin_views import AdminLogsResponse, AdminCredentialStatus

from . import logs, users, credentials

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(users._require_admin)])
router.add_api_route("/users", users.list_users, methods=["GET"])
router.add_api_route("/users", users.create_user, methods=["POST"], status_code=201)
router.add_api_route("/users/{user_id}", users.get_user, methods=["GET"])
router.add_api_route("/users/{user_id}", users.update_user, methods=["PUT"])
router.add_api_route("/users/{user_id}", users.delete_user, methods=["DELETE"])
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

"""Área administrativa: mesmos handlers, com autorização também no prefixo."""
from fastapi import APIRouter, Depends, Query

from ..admin_metrics import AdminMetricsResponse, collect_admin_metrics
from ..database import supabase
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


@router.get("/location-points")
async def location_points():
    """Admin-only consented approximate coordinates; one current record per account."""
    result = supabase.table("account_location_sharing").select("user_id,latitude,longitude,accuracy_m,collected_at").eq("choice","accepted").execute()
    return {"points":[{"account":str(row["user_id"])[:8],"latitude":float(row["latitude"]),
                       "longitude":float(row["longitude"]),"accuracy_m":row.get("accuracy_m"),
                       "collected_at":row["collected_at"]}
                      for row in (result.data or []) if row.get("latitude") is not None and row.get("longitude") is not None]}

"""Área administrativa: mesmos handlers, com autorização também no prefixo."""
from fastapi import APIRouter, Depends, Query

from ..admin_metrics import AdminMetricsResponse, collect_admin_metrics
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

"""Área administrativa: mesmos handlers, com autorização também no prefixo."""
from fastapi import APIRouter, Depends, Query

from ..admin_metrics import AdminMetricsResponse, collect_admin_metrics

from . import logs, users

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(users._require_admin)])
router.add_api_route("/users", users.list_users, methods=["GET"])
router.add_api_route("/users", users.create_user, methods=["POST"], status_code=201)
router.add_api_route("/users/{user_id}", users.get_user, methods=["GET"])
router.add_api_route("/users/{user_id}", users.update_user, methods=["PUT"])
router.add_api_route("/users/{user_id}", users.delete_user, methods=["DELETE"])
router.add_api_route("/logs", logs.list_logs, methods=["GET"])


@router.get("/metrics", response_model=AdminMetricsResponse)
async def metrics(days: int = Query(30, ge=7, le=90)):
    return await collect_admin_metrics(days)

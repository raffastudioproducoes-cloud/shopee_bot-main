"""Contagens operacionais de publicacao, sem confundir com insights das redes."""

from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from apis.meta_version import GRAPH_URL, GRAPH_VERSION
from ..crypto import decrypt
from ..database import supabase
from ..profiles import scope_owner
from .auth import get_current_user_id
from .credentials import _check_test_rate_limit
from .profiles import get_current_profile_id

router = APIRouter(prefix="/analytics", tags=["analytics"])

Network = Literal["threads", "facebook", "instagram", "tiktok", "x"]
NETWORKS: tuple[Network, ...] = ("threads", "facebook", "instagram", "tiktok", "x")
STATUSES = ("succeeded", "failed", "unknown")
_INSIGHT_PROBES = {
    "threads": ("threads_credentials", "t_user_id", "access_token", "views", None),
    "instagram": ("instagram_credentials", "ig_user_id", "user_access_token", "reach", "day"),
    "facebook": ("facebook_credentials", "page_id", "page_access_token", "page_media_view", "day"),
}


@router.post("/probe/{network}")
async def probe_insights(
    network: str,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Read one account/page metric using this profile's existing OAuth token."""
    if network not in _INSIGHT_PROBES:
        raise HTTPException(status_code=404, detail="Rede sem sonda de insights")
    if not profile_id:
        raise HTTPException(status_code=400, detail="Selecione um perfil")
    _check_test_rate_limit(user_id)
    table, id_column, token_column, metric, period = _INSIGHT_PROBES[network]
    row = scope_owner(
        supabase.table(table).select(f"{id_column},{token_column}"), user_id, profile_id
    ).maybe_single().execute()
    data = row.data if row else None
    if not data or not data.get(id_column) or not data.get(token_column):
        return {"network": network, "state": "not_connected"}

    host = "https://graph.threads.net/v1.0" if network == "threads" else f"{GRAPH_URL}/{GRAPH_VERSION}"
    endpoint = "threads_insights" if network == "threads" else "insights"
    params = {"metric": metric}
    if period:
        params["period"] = period
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{host}/{data[id_column]}/{endpoint}",
                params=params,
                headers={"Authorization": f"Bearer {decrypt(data[token_column])}"},
            )
    except httpx.RequestError:
        return {"network": network, "state": "network_error"}
    if response.status_code != 200:
        try:
            body = response.json()
            error = body.get("error", {}) if isinstance(body, dict) else {}
        except ValueError:
            error = {}
        return {
            "network": network,
            "state": "api_error",
            "http_status": response.status_code,
            "error_code": error.get("code") if isinstance(error, dict) else None,
            "error_subcode": error.get("error_subcode") if isinstance(error, dict) else None,
        }
    try:
        body = response.json()
    except ValueError:
        return {"network": network, "state": "invalid_response"}
    if not isinstance(body, dict) or not isinstance(body.get("data"), list):
        return {"network": network, "state": "invalid_response"}
    values = body["data"]
    return {
        "network": network,
        "state": "ok" if values else "no_data",
        "metric": metric,
        "result_count": len(values),
    }


def _count_jobs(user_id: int, profile_id: str, network: Network, status: str, since: str) -> int:
    query = scope_owner(
        supabase.table("publish_jobs").select("id", count="exact"), user_id, profile_id
    )
    return query.eq("network", network).eq("status", status).gte("finished_at", since).limit(1).execute().count or 0


@router.get("/summary")
def summary(
    days: int = Query(30),
    network: Network | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
    if not profile_id:
        return {"days": days, "networks": []}
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = []
    for name in (network,) if network else NETWORKS:
        counts = {status: _count_jobs(user_id, profile_id, name, status, since) for status in STATUSES}
        rows.append({
            "network": name,
            **counts,
            "views": None,
            "likes": None,
            "comments": None,
            "reposts": None,
            "clicks": None,
            "insights_status": "not_collected",
        })
    return {"days": days, "networks": rows}

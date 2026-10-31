"""Contagens operacionais de publicacao, sem confundir com insights das redes."""

from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from apis.meta_version import GRAPH_URL, GRAPH_VERSION
from ..analytics_refresh import TABLE as REFRESH_TABLE, refresh_account
from ..crypto import decrypt
from ..database import supabase
from ..profiles import scope_owner
from .auth import get_current_user_id
from .credentials import _check_test_rate_limit, _require_admin
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


def _facebook_daily_views(metrics: list) -> list[dict] | None:
    """Only return validated daily counts and UTC period ends, never raw Graph payloads."""
    counts: dict[str, int] = {}
    for metric in metrics:
        if not isinstance(metric, dict) or metric.get("name") != "page_media_view":
            return None
        values = metric.get("values")
        if not isinstance(values, list):
            return None
        for entry in values:
            if not isinstance(entry, dict):
                return None
            value, end_time = entry.get("value"), entry.get("end_time")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0 or not isinstance(end_time, str):
                return None
            try:
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                return None
            if end.tzinfo is None:
                return None
            period_end = end.astimezone(timezone.utc).date().isoformat()
            counts[period_end] = value
    return [{"period_end": day, "value": counts[day]} for day in sorted(counts)]


@router.post("/probe/{network}")
async def probe_insights(
    network: str,
    days: int = Query(30),
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Read one account/page metric using this profile's existing OAuth token."""
    if network not in _INSIGHT_PROBES:
        raise HTTPException(status_code=404, detail="Rede sem sonda de insights")
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
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
    if network == "facebook":
        # Explicit interval instead of the Graph API's default last two periods.
        # The returned metric periods are UTC boundaries and may cover fewer days.
        today = datetime.now(timezone.utc).date()
        params["since"] = (today - timedelta(days=days - 1)).isoformat()
        params["until"] = (today + timedelta(days=1)).isoformat()
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
    if network == "facebook":
        daily_values = _facebook_daily_views(values)
        if daily_values is None:
            return {"network": network, "state": "invalid_response"}
        return {
            "network": network,
            "state": "ok" if daily_values else "no_data",
            "metric": metric,
            "result_count": len(values),
            "days_requested": days,
            "days_returned": len(daily_values),
            "total_views": sum(v["value"] for v in daily_values) if daily_values else None,
            "daily_values": daily_values,
        }
    return {
        "network": network,
        "state": "ok" if values else "no_data",
        "metric": metric,
        "result_count": len(values),
    }


@router.post("/refresh")
async def refresh_information(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    if not profile_id:
        raise HTTPException(status_code=400, detail="Selecione um perfil")
    return await refresh_account(user_id, profile_id, manual=True)


def _read_refresh(user_id, profile_id):
    response = scope_owner(
        supabase.table(REFRESH_TABLE).select(
            "last_attempt_at,last_completed_at,provider_states,facebook_daily_values,metrics_collected_at"
        ), user_id, profile_id
    ).maybe_single().execute()
    return response.data if response else None


def _facebook_views_for_period(refresh, days):
    if not refresh or (refresh.get("provider_states") or {}).get("facebook") != "ok":
        return None
    values = refresh.get("facebook_daily_values")
    if not isinstance(values, list) or not values:
        return None
    start_day = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()
    total = 0
    has_value = False
    for item in values:
        if not isinstance(item, dict):
            return None
        day, value = item.get("period_end"), item.get("value")
        if not isinstance(day, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return None
        if day >= start_day:
            total += value
            has_value = True
    return total if has_value else None


def _count_jobs(user_id: int, profile_id: str, network: Network, status: str, since: str) -> int:
    query = scope_owner(
        supabase.table("publish_jobs").select("id", count="exact"), user_id, profile_id
    )
    return query.eq("network", network).eq("status", status).gte("finished_at", since).limit(1).execute().count or 0


@router.get("/summary")
def summary(
    background_tasks: BackgroundTasks,
    days: int = Query(30),
    network: Network | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
    if not profile_id:
        return {"days": days, "networks": []}
    # A leitura permanece rápida. Uma tarefa após a resposta registra o perfil
    # e consulta provedores somente se o claim diário estiver vencido.
    background_tasks.add_task(refresh_account, user_id, profile_id)
    refresh = _read_refresh(user_id, profile_id)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = []
    for name in (network,) if network else NETWORKS:
        counts = {status: _count_jobs(user_id, profile_id, name, status, since) for status in STATUSES}
        rows.append({
            "network": name,
            **counts,
            "views": _facebook_views_for_period(refresh, days) if name == "facebook" else None,
            "likes": None,
            "comments": None,
            "reposts": None,
            "clicks": None,
            "insights_status": (refresh.get("provider_states") or {}).get(name, "not_collected") if refresh else "not_collected",
        })
    return {
        "days": days, "networks": rows,
        "last_attempt_at": refresh.get("last_attempt_at") if refresh else None,
        "last_completed_at": refresh.get("last_completed_at") if refresh else None,
        "provider_states": refresh.get("provider_states") if refresh else {},
        "auto_refresh_hours": 24,
    }


@router.get("/timeline")
def timeline(
    days: int = Query(30),
    network: Network | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Daily terminal-state counts scoped to the authenticated account and active profile.

    The RPC performs SQL aggregation (max. 91 UTC calendar dates) and returns no
    post text, provider identifiers, credentials, or other users' data.
    """
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
    if not profile_id:
        return {"days": days, "points": []}
    try:
        response = supabase.rpc("analytics_daily_job_counts", {
            "p_user_id": user_id,
            "p_profile_id": profile_id,
            "p_days": days,
            "p_network": network,
        }).execute()
    except Exception:
        # Never expose internal SQL/client details in a public endpoint.
        raise HTTPException(status_code=503, detail="Histórico de análises temporariamente indisponível")
    return {"days": days, "points": response.data or []}

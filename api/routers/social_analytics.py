"""Contagens operacionais de publicacao, sem confundir com insights das redes."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from ..analytics_refresh import (TABLE as REFRESH_TABLE, claim_manual_refresh,
                                 manual_quota_status, refresh_account)
from ..database import supabase
from ..post_insights import (current_network_connections, distinct_published_jobs,
                             indexed_insights, published_jobs, summarize_post_metrics)
from ..profiles import scope_account, scope_owner
from .auth import get_current_user_id
from .credentials import _check_test_rate_limit, _require_admin
from .profiles import get_current_profile_id

router = APIRouter(prefix="/analytics", tags=["analytics"])

Network = Literal["threads", "facebook", "instagram", "tiktok", "x"]
NETWORKS: tuple[Network, ...] = ("threads", "facebook", "instagram", "tiktok", "x")
STATUSES = ("succeeded", "failed", "unknown")
_TIMELINE_PAGE_SIZE = 500


def _analytics_profile(user_id, requested: str | None, active: str | None) -> tuple[str | None, bool]:
    """Resolve the viewer-only selection without changing the session's active profile."""
    if requested is None:
        return active, False  # Backward-compatible default for existing clients.
    if requested == "all":
        return None, True
    try:
        selected = str(UUID(requested))
    except ValueError:
        raise HTTPException(status_code=422, detail="Perfil inválido")
    try:
        owned = (supabase.table("profiles").select("id")
                 .eq("user_id", user_id).eq("id", selected).maybe_single().execute())
    except Exception:
        raise HTTPException(status_code=503, detail="Perfis temporariamente indisponíveis")
    if not owned or not owned.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return selected, False


def _account_profile_ids(user_id) -> list[str]:
    """Include archived profiles in account history; the selector lists active profiles."""
    ids = []
    offset = 0
    while True:
        rows = (scope_account(supabase.table("profiles").select("id"), user_id)
                .order("id").range(offset, offset + _TIMELINE_PAGE_SIZE - 1).execute()).data or []
        ids.extend(row["id"] for row in rows)
        if len(rows) < _TIMELINE_PAGE_SIZE:
            return ids
        offset += _TIMELINE_PAGE_SIZE


def _unassigned_history(user_id, days: int, network: Network | None) -> list[dict]:
    """Only legacy rows with profile_id=NULL need a REST scan; regular profiles use the SQL RPC."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    offset = 0
    totals: dict[tuple[str, str, str], int] = {}
    while True:
        query = (scope_account(supabase.table("publish_jobs").select("id,finished_at,network,status"), user_id)
                 .is_("profile_id", "null").gte("finished_at", since)
                 .in_("status", list(STATUSES)))
        query = query.eq("network", network) if network else query.in_("network", list(NETWORKS))
        rows = (query.order("finished_at").order("id").range(
            offset, offset + _TIMELINE_PAGE_SIZE - 1
        ).execute()).data or []
        for item in rows:
            end = datetime.fromisoformat(item["finished_at"].replace("Z", "+00:00"))
            if end.tzinfo is None:
                raise ValueError("Invalid unassigned history timestamp")
            key = (end.astimezone(timezone.utc).date().isoformat(), item["network"], item["status"])
            totals[key] = totals.get(key, 0) + 1
        if len(rows) < _TIMELINE_PAGE_SIZE:
            break
        offset += _TIMELINE_PAGE_SIZE
    return [{"day": day, "network": name, "status": status, "total": amount}
            for (day, name, status), amount in totals.items()]


def _account_timeline(user_id, days: int, network: Network | None) -> list[dict]:
    """Merge owned profiles' RPC aggregates plus unassigned history; never cross account boundaries."""
    totals: dict[tuple[str, str, str], int] = {}
    for selected in _account_profile_ids(user_id):
        response = supabase.rpc("analytics_daily_job_counts", {
            "p_user_id": user_id, "p_profile_id": selected,
            "p_days": days, "p_network": network,
        }).execute()
        for item in response.data or []:
            key = (item["day"], item["network"], item["status"])
            amount = int(item["total"])
            if amount < 0 or item["network"] not in NETWORKS or item["status"] not in STATUSES:
                raise ValueError("Invalid aggregated history row")
            totals[key] = totals.get(key, 0) + amount
    for item in _unassigned_history(user_id, days, network):
        key = (item["day"], item["network"], item["status"])
        totals[key] = totals.get(key, 0) + item["total"]
    return [{"day": day, "network": name, "status": status, "total": total}
            for (day, name, status), total in sorted(totals.items())]


@router.post("/probe/{network}")
async def probe_insights(
    network: str,
    days: int = Query(30),
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Admin: valida cache de publicação individual, sem consultar contas ou Páginas."""
    if network not in NETWORKS:
        raise HTTPException(status_code=404, detail="Rede não reconhecida")
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
    profile_id, all_profiles = _analytics_profile(user_id, selected_profile_id, profile_id)
    if all_profiles or not profile_id:
        raise HTTPException(status_code=400, detail="Selecione um perfil")
    _check_test_rate_limit(user_id)
    jobs = distinct_published_jobs(published_jobs(user_id, profile_id, days, network))
    if not jobs:
        return {"network": network, "state": "no_posts", "post_count": 0}
    selected = next((job for job in jobs if job.get("external_id")), None)
    if not selected:
        return {"network": network, "state": "missing_external_id", "post_count": len(jobs)}
    index = indexed_insights(user_id, [selected])
    item = index.get(selected["id"])
    if not item or item.get("external_id") != selected["external_id"]:
        return {"network": network, "state": "not_collected", "post_count": len(jobs)}
    return {"network": network, "state": item["state"], "post_count": len(jobs),
            "metric": "views", "total_views": item.get("views") if item["state"] == "ok" else None}


@router.post("/refresh")
async def refresh_information(
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile_id, all_profiles = _analytics_profile(user_id, selected_profile_id, profile_id)
    if not all_profiles and not profile_id:
        raise HTTPException(status_code=400, detail="Selecione um perfil")
    try:
        profile_ids = _account_profile_ids(user_id) if all_profiles else [profile_id]
    except Exception:
        raise HTTPException(status_code=503, detail="Não foi possível consultar os perfis")
    if not profile_ids:
        raise HTTPException(status_code=400, detail="Nenhum perfil disponível para atualização")
    if len(profile_ids) > 12:
        raise HTTPException(status_code=422, detail="Selecione um perfil para atualizar; limite de 12 por solicitação")
    try:
        claim = await asyncio.to_thread(claim_manual_refresh, user_id, profile_ids)
    except Exception:
        raise HTTPException(status_code=503, detail="Controle de atualizações temporariamente indisponível")
    if not isinstance(claim, dict) or not isinstance(claim.get("quota"), dict):
        raise HTTPException(status_code=503, detail="Controle de atualizações temporariamente indisponível")
    if claim.get("state") == "limit_reached":
        raise HTTPException(status_code=429, detail="Limite de 10 atualizações por dia atingido")
    if claim.get("state") == "recent":
        return {"state": "recent", "quota": claim["quota"], "updated_profiles": 0}
    tokens = claim.get("claims")
    if claim.get("state") != "accepted" or not isinstance(tokens, dict) or not tokens:
        raise HTTPException(status_code=503, detail="Controle de atualizações temporariamente indisponível")
    # Os claims são obtidos pelo backend; nunca chegam ao cliente, nem aos logs.
    gate = asyncio.Semaphore(3)

    async def collect(selected, token):
        async with gate:
            return await refresh_account(user_id, selected, manual=True, claim_token=token)

    await asyncio.gather(*(collect(selected, token) for selected, token in tokens.items()))
    return {"state": "updated", "quota": claim["quota"], "updated_profiles": len(tokens)}


@router.get("/refresh/quota")
def refresh_quota(user_id: int = Depends(get_current_user_id)):
    try:
        quota = manual_quota_status(user_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Cota de atualizações indisponível")
    if not isinstance(quota, dict) or not isinstance(quota.get("unlimited"), bool):
        raise HTTPException(status_code=503, detail="Cota de atualizações indisponível")
    return quota


def _read_refresh(user_id, profile_id):
    response = scope_owner(
        supabase.table(REFRESH_TABLE).select(
            "last_attempt_at,last_completed_at,provider_states,metrics_collected_at"
        ), user_id, profile_id
    ).maybe_single().execute()
    return response.data if response else None


def _count_jobs(user_id: int, profile_id: str | None, network: Network, status: str, since: str) -> int:
    query = scope_account(supabase.table("publish_jobs").select("id", count="exact"), user_id)
    if profile_id is not None:
        query = query.eq("profile_id", profile_id)
    try:
        response = query.eq("network", network).eq("status", status).gte("finished_at", since).limit(1).execute()
    except Exception:
        raise HTTPException(status_code=503, detail="Contagem de análises temporariamente indisponível")
    if response.count is None:
        raise HTTPException(status_code=503, detail="Contagem de análises temporariamente indisponível")
    return response.count


@router.get("/summary")
def summary(
    background_tasks: BackgroundTasks,
    days: int = Query(30),
    network: Network | None = None,
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
    profile_id, all_profiles = _analytics_profile(user_id, selected_profile_id, profile_id)
    if not all_profiles and not profile_id:
        return {"days": days, "networks": []}
    refresh = _read_refresh(user_id, profile_id) if not all_profiles else None
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        jobs = distinct_published_jobs(published_jobs(user_id, profile_id, days, network))
        index = indexed_insights(user_id, jobs)
        connections = current_network_connections(user_id, profile_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Insights de publicações temporariamente indisponíveis")
    # Em Todos, consultar somente perfis com posts no período. Claim por perfil
    # impede duplicação com a rotina diária; lote evita tempestade de OAuth.
    targets = sorted({job["profile_id"] for job in jobs if job.get("profile_id")})[:12] if all_profiles else [profile_id]
    for selected in targets:
        background_tasks.add_task(refresh_account, user_id, selected)
    rows = []
    for name in (network,) if network else NETWORKS:
        counts = {status: _count_jobs(user_id, profile_id, name, status, since) for status in STATUSES}
        subset = [job for job in jobs if job["network"] == name]
        metrics, collected, eligible, states = summarize_post_metrics(subset, index)
        if name in ("x", "tiktok"):
            status = "unsupported"
        elif not connections.get(name, False):
            status = "not_connected"
        elif name != "threads":
            status = "unsupported"
        elif not subset:
            status = "no_posts"
        elif not eligible:
            status = "missing_external_id"
        elif collected == eligible:
            status = "ok"
        elif collected:
            status = "partial"
        elif len(states) == 1:
            status = next(iter(states))
        else:
            status = "not_collected"
        if name != "threads":
            # Não existe coletor individual homologado nessas redes ainda.
            metrics = {field: None for field in metrics}
        rows.append({
            "network": name,
            **counts,
            **metrics,
            "insights_status": status,
            "posts_with_insights": collected,
            "posts_with_external_id": eligible,
        })
    return {
        "days": days, "networks": rows,
        "last_attempt_at": refresh.get("last_attempt_at") if refresh else None,
        "last_completed_at": refresh.get("last_completed_at") if refresh else None,
        "provider_states": {row["network"]: row["insights_status"] for row in rows},
        "auto_refresh_hours": 24,
        "metrics_scope": "confirmed_publications_only",
        "metrics_window": "lifetime_of_posts_published_in_selected_period",
    }


@router.get("/posts")
def post_performance(
    days: int = Query(30),
    network: Network | None = None,
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Ranking de posts confirmados; jamais mistura insights gerais de contas."""
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
    profile_id, all_profiles = _analytics_profile(user_id, selected_profile_id, profile_id)
    if not all_profiles and not profile_id:
        return {"days": days, "posts": []}
    try:
        jobs = distinct_published_jobs(published_jobs(user_id, profile_id, days, network))
        index = indexed_insights(user_id, jobs)
        # Carrega texto apenas após validar a titularidade de todos os jobs.
        post_ids = list({job["post_id"] for job in jobs if job.get("post_id") is not None})
        previews = {}
        for offset in range(0, len(post_ids), _TIMELINE_PAGE_SIZE):
            response = scope_owner(
                supabase.table("posts").select("post_id,id,text"), user_id, profile_id
            ).in_("post_id", post_ids[offset:offset + _TIMELINE_PAGE_SIZE]).order("id").execute() if profile_id else scope_account(
                supabase.table("posts").select("post_id,id,text"), user_id
            ).in_("post_id", post_ids[offset:offset + _TIMELINE_PAGE_SIZE]).order("id").execute()
            for item in response.data or []:
                previews.setdefault(item["post_id"], item.get("text") or "")
    except Exception:
        raise HTTPException(status_code=503, detail="Desempenho por publicação temporariamente indisponível")
    posts = []
    for job in jobs:
        metrics, collected, _, states = summarize_post_metrics([job], index)
        state = next(iter(states)) if len(states) == 1 else "not_collected"
        item = index.get(job["id"])
        preview = previews.get(job.get("post_id"), "")
        if not preview:
            # Legado: o registro de texto pode ter sido removido após o envio.
            # Identificador parcial do post permite distingui-lo sem inventar copy.
            external = job.get("external_id")
            preview = (f"Publicação · ID final {external[-8:]}" if external
                       else "Publicação histórica sem conteúdo preservado")
        posts.append({
            "job_id": job["id"], "network": job["network"],
            "profile_id": job["profile_id"], "finished_at": job["finished_at"],
            "preview": preview[:160], "state": state if collected or states else (
                "not_collected" if job.get("external_id") else "missing_external_id"
            ),
            **metrics,
            "last_completed_at": item.get("last_completed_at") if collected and item else None,
        })
    posts.sort(key=lambda item: (item["views"] is None, -(item["views"] or 0),
                                 item["finished_at"] or ""))
    return {"days": days, "posts": posts[:150], "total_posts": len(posts),
            "truncated": len(posts) > 150,
            "metrics_window": "lifetime_of_posts_published_in_selected_period"}


@router.get("/timeline")
def timeline(
    days: int = Query(30),
    network: Network | None = None,
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Daily terminal-state counts scoped to the authenticated account and active profile.

    The RPC performs SQL aggregation (max. 91 UTC calendar dates) and returns no
    post text, provider identifiers, credentials, or other users' data.
    """
    if days not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="Período inválido")
    profile_id, all_profiles = _analytics_profile(user_id, selected_profile_id, profile_id)
    if not all_profiles and not profile_id:
        return {"days": days, "points": []}
    try:
        if all_profiles:
            points = _account_timeline(user_id, days, network)
        else:
            response = supabase.rpc("analytics_daily_job_counts", {
                "p_user_id": user_id,
                "p_profile_id": profile_id,
                "p_days": days,
                "p_network": network,
            }).execute()
            points = response.data or []
    except Exception:
        # Never expose internal SQL/client details in a public endpoint.
        raise HTTPException(status_code=503, detail="Histórico de análises temporariamente indisponível")
    return {"days": days, "points": points}

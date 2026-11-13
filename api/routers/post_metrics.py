"""Métricas por postagem: lista, ranking (post e rede) e evolução pelo histórico.

Somente publicações confirmadas da própria conta (scope_account + ownership do perfil
via _analytics_profile). Métrica ausente na rede = null (a UI mostra "—"), nunca zero.
Cliques vêm só do redirecionador próprio (/r/{token}); sem token = null.
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from shopee_bot.utils.timezones import DEFAULT_TIMEZONE, normalize_timezone

from ..database import supabase
from ..post_insights import HISTORY_TABLE, combined_shares, distinct_published_jobs, indexed_insights
from ..profiles import scope_account
from .auth import get_current_user_id
from .profiles import get_current_profile_id
from .social_analytics import Network, _analytics_profile

router = APIRouter(prefix="/analytics", tags=["analytics"])

PERIOD_DAYS = (7, 30, 90, 180, 365)
MAX_RANGE_DAYS = 365
MAX_JOBS = 5000  # ponytail: agregação em Python; trocar por RPC SQL se alguma conta passar disso.
MAX_HISTORY_ROWS = 20000
_PAGE = 500
METRIC_FIELDS = ("views", "reach", "likes", "comments", "shares", "saves", "clicks")
RankMetric = Literal["views", "likes", "comments", "shares", "clicks"]
SortField = Literal["views", "likes", "comments", "shares", "clicks", "finished_at"]
USABLE_STATES = {"ok": "ok", "multipart_unmapped": "parcial"}


def _zone(tz: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(normalize_timezone(tz or DEFAULT_TIMEZONE))
    except ValueError:
        raise HTTPException(status_code=422, detail="Fuso horário inválido")


def resolve_period(days: int | None, start: date | None, end: date | None, zone: ZoneInfo,
                   today: date | None = None) -> tuple[datetime, datetime, int]:
    """[início, fim) em UTC. Dias fixos ou intervalo personalizado de até 365 dias."""
    today = today or datetime.now(zone).date()
    if start is not None or end is not None:
        if start is None or end is None:
            raise HTTPException(status_code=422, detail="Informe início e fim do período")
        if end < start:
            raise HTTPException(status_code=422, detail="Fim do período antes do início")
        if end > today:
            raise HTTPException(status_code=422, detail="Período no futuro")
        if (end - start).days + 1 > MAX_RANGE_DAYS:
            raise HTTPException(status_code=422, detail="Período máximo de 365 dias")
    else:
        days = 30 if days is None else days
        if days not in PERIOD_DAYS:
            raise HTTPException(status_code=422, detail="Período inválido")
        start, end = today - timedelta(days=days - 1), today
    begin = datetime.combine(start, time.min, zone).astimezone(timezone.utc)
    finish = datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    return begin, finish, (end - start).days + 1


def _paged(query_factory, cap):
    rows, offset = [], 0
    while len(rows) < cap:
        page = (query_factory().range(offset, offset + _PAGE - 1).execute()).data or []
        rows.extend(page)
        if len(page) < _PAGE:
            break
        offset += _PAGE
    return rows[:cap], len(rows) >= cap


def _jobs(user_id, profile_id, network, begin, finish):
    def query():
        q = (scope_account(supabase.table("publish_jobs").select(
            "id,post_id,profile_id,network,external_id,finished_at"), user_id)
            .eq("status", "succeeded").gte("finished_at", begin.isoformat())
            .lt("finished_at", finish.isoformat()))
        q = q.eq("profile_id", profile_id) if profile_id else q
        q = q.eq("network", network) if network else q
        return q.order("finished_at", desc=True).order("id")
    jobs, truncated = _paged(query, MAX_JOBS)
    return distinct_published_jobs(jobs), truncated


def _click_tokens(user_id, job_ids):
    """publish_job_id -> {token: clicks}; só tokens da própria conta."""
    tokens = {}
    for offset in range(0, len(job_ids), _PAGE):
        rows = (scope_account(supabase.table("post_link_clicks").select(
            "publish_job_id,token,clicks"), user_id)
            .in_("publish_job_id", job_ids[offset:offset + _PAGE]).execute()).data or []
        for row in rows:
            tokens.setdefault(row["publish_job_id"], {})[row["token"]] = int(row.get("clicks") or 0)
    return tokens


def _previews(user_id, post_ids):
    previews = {}
    for offset in range(0, len(post_ids), _PAGE):
        rows = (scope_account(supabase.table("posts").select("id,text"), user_id)
                .in_("id", post_ids[offset:offset + _PAGE]).execute()).data or []
        for row in rows:
            previews[row["id"]] = (row.get("text") or "")[:160]
    return previews


def post_row(job, item, tokens, preview):
    """Linha de um envio: última coleta do cache publication_insights + cliques próprios."""
    usable = bool(item) and item.get("network") == job["network"] and (
        item.get("external_id") == job.get("external_id")) and item.get("state") in USABLE_STATES
    row = {field: None for field in METRIC_FIELDS}
    if usable:
        row.update(views=item.get("views"), likes=item.get("likes"),
                   comments=item.get("comments"), shares=combined_shares(item))
    row["clicks"] = sum(tokens.values()) if tokens else None
    if usable:
        status = USABLE_STATES[item["state"]]
    elif item and item.get("state"):
        status = item["state"]
    else:
        status = "not_collected" if job.get("external_id") else "missing_external_id"
    return {
        "job_id": job["id"], "post_id": job.get("post_id"), "network": job["network"],
        "profile_id": job.get("profile_id"), "finished_at": job.get("finished_at"),
        "preview": preview or "Publicação sem texto preservado", "status": status,
        "collected_at": item.get("last_completed_at") if usable else None, **row,
    }


def _rows(user_id, profile_id, network, begin, finish):
    jobs, truncated = _jobs(user_id, profile_id, network, begin, finish)
    ids = [job["id"] for job in jobs]
    index = indexed_insights(user_id, jobs) if jobs else {}
    tokens = _click_tokens(user_id, ids) if ids else {}
    previews = _previews(user_id, list({job["post_id"] for job in jobs if job.get("post_id") is not None}))
    return [post_row(job, index.get(job["id"]), tokens.get(job["id"]), previews.get(job.get("post_id")))
            for job in jobs], truncated


def sort_rows(rows, field, descending=True):
    """Nulos sempre no fim, em qualquer direção; empate pela data mais recente."""
    present = [row for row in rows if row.get(field) is not None]
    missing = [row for row in rows if row.get(field) is None]
    present.sort(key=lambda row: (row[field], row.get("finished_at") or ""), reverse=descending)
    missing.sort(key=lambda row: row.get("finished_at") or "", reverse=True)
    return present + missing


def network_ranking(rows, metric):
    """Soma e média por post medido; `posts_measured` evita comparar 1 post com 50."""
    result = {}
    for row in rows:
        entry = result.setdefault(row["network"], {"network": row["network"], "posts": 0,
                                                   "posts_measured": 0, "total": None})
        entry["posts"] += 1
        if row.get(metric) is not None:
            entry["posts_measured"] += 1
            entry["total"] = (entry["total"] or 0) + row[metric]
    for entry in result.values():
        entry["average"] = round(entry["total"] / entry["posts_measured"], 2) if entry["posts_measured"] else None
    return sorted(result.values(), key=lambda e: (e["total"] is None, -(e["total"] or 0), e["network"]))


def _scope(user_id, selected, active):
    profile_id, all_profiles = _analytics_profile(user_id, selected, active)
    return profile_id, all_profiles or bool(profile_id)


def _period_info(begin, finish, length):
    return {"from": begin.isoformat(), "to": finish.isoformat(), "days": length}


@router.get("/post-metrics")
def list_post_metrics(
    network: Network | None = None,
    days: int | None = Query(None),
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    tz: str | None = Query(None, max_length=64),
    sort: SortField = "views",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=MAX_JOBS),
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Por post: rede, texto resumido, publicado em, última métrica e total de cliques."""
    begin, finish, length = resolve_period(days, start, end, _zone(tz))
    profile_id, allowed = _scope(user_id, selected_profile_id, profile_id)
    if not allowed:
        return {"posts": [], "total": 0, "limit": limit, "offset": offset, "truncated": False,
                "period": _period_info(begin, finish, length)}
    try:
        rows, truncated = _rows(user_id, profile_id, network, begin, finish)
    except Exception:
        raise HTTPException(status_code=503, detail="Métricas por publicação temporariamente indisponíveis")
    ordered = sort_rows(rows, sort, order == "desc")
    return {"posts": ordered[offset:offset + limit], "total": len(rows), "limit": limit,
            "offset": offset, "truncated": truncated, "period": _period_info(begin, finish, length),
            "metrics_window": "lifetime_of_posts_published_in_selected_period"}


@router.get("/ranking")
def ranking(
    metric: RankMetric = "views",
    top: int = Query(10, ge=1, le=50),
    network: Network | None = None,
    days: int | None = Query(None),
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    tz: str | None = Query(None, max_length=64),
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Melhores posts pela métrica e ranking de redes (soma e média por post medido)."""
    begin, finish, length = resolve_period(days, start, end, _zone(tz))
    profile_id, allowed = _scope(user_id, selected_profile_id, profile_id)
    if not allowed:
        return {"metric": metric, "posts": [], "networks": [], "period": _period_info(begin, finish, length)}
    try:
        rows, truncated = _rows(user_id, profile_id, network, begin, finish)
    except Exception:
        raise HTTPException(status_code=503, detail="Ranking temporariamente indisponível")
    measured = [row for row in rows if row.get(metric) is not None]
    return {"metric": metric, "posts": sort_rows(measured, metric)[:top],
            "networks": network_ranking(rows, metric), "truncated": truncated,
            "period": _period_info(begin, finish, length)}


def daily_series(rows, begin, length, zone):
    """Total acumulado por rede e dia local: último valor de cada post no dia, levado adiante."""
    first_day = begin.astimezone(zone).date()
    days = [first_day + timedelta(days=i) for i in range(length)]
    by_day = {}  # network -> day -> job -> último row do dia
    for row in sorted(rows, key=lambda r: r["collected_at"]):
        stamp = datetime.fromisoformat(str(row["collected_at"]).replace("Z", "+00:00"))
        by_day.setdefault(row["network"], {}).setdefault(
            stamp.astimezone(zone).date(), {})[row["publish_job_id"]] = row
    points = []
    for network in sorted(by_day):
        carried = {}
        for day in days:
            carried.update(by_day[network].get(day, {}))
            point = {"day": day.isoformat(), "network": network}
            for field in ("views", "likes", "comments", "shares"):
                values = [row.get(field) for row in carried.values() if row.get(field) is not None]
                point[field] = sum(values) if values else None
            points.append(point)
    return points


def _clicks_by_day(user_id, profile_id, network, job_id, begin, finish):
    query = scope_account(supabase.table("post_link_clicks").select("token,network"), user_id)
    query = query.eq("profile_id", profile_id) if profile_id else query
    query = query.eq("network", network) if network else query
    query = query.eq("publish_job_id", job_id) if job_id else query
    tokens = {row["token"]: row["network"] for row in (query.limit(MAX_JOBS).execute()).data or []}
    totals = {}
    names = list(tokens)
    for offset in range(0, len(names), _PAGE):
        rows = (supabase.table("post_link_click_days").select("token,day,clicks")
                .in_("token", names[offset:offset + _PAGE])
                .gte("day", begin.date().isoformat()).lte("day", finish.date().isoformat())
                .execute()).data or []
        for row in rows:
            key = (row["day"], tokens[row["token"]])
            totals[key] = totals.get(key, 0) + int(row.get("clicks") or 0)
    return [{"day": day, "network": net, "clicks": value} for (day, net), value in sorted(totals.items())]


@router.get("/series")
def series(
    job_id: UUID | None = None,
    network: Network | None = None,
    days: int | None = Query(None),
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    tz: str | None = Query(None, max_length=64),
    selected_profile_id: str | None = Query(None, alias="profile_id"),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Evolução pelo histórico de coletas (post_metrics), filtrada pela data da coleta."""
    zone = _zone(tz)
    begin, finish, length = resolve_period(days, start, end, zone)
    profile_id, allowed = _scope(user_id, selected_profile_id, profile_id)
    empty = {"points": [], "clicks": [], "truncated": False, "period": _period_info(begin, finish, length)}
    if not allowed:
        return empty
    job = str(job_id) if job_id else None
    try:
        if job:
            owned = scope_account(supabase.table("publish_jobs").select("id,network"), user_id).eq("id", job)
            owned = owned.eq("profile_id", profile_id) if profile_id else owned
            if not (owned.limit(1).execute()).data:
                raise HTTPException(status_code=404, detail="Publicação não encontrada")

        def query():
            q = (scope_account(supabase.table(HISTORY_TABLE).select(
                "publish_job_id,network,collected_at,window_label,status,views,likes,comments,shares"), user_id)
                .in_("status", ["ok", "parcial"]).gte("collected_at", begin.isoformat())
                .lt("collected_at", finish.isoformat()))
            q = q.eq("profile_id", profile_id) if profile_id else q
            q = q.eq("network", network) if network else q
            q = q.eq("publish_job_id", job) if job else q
            return q.order("collected_at").order("id")
        rows, truncated = _paged(query, MAX_HISTORY_ROWS)
        clicks = _clicks_by_day(user_id, profile_id, network, job, begin, finish)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Histórico de métricas temporariamente indisponível")
    points = rows if job else daily_series(rows, begin, length, zone)
    return {**empty, "points": points, "clicks": clicks, "truncated": truncated,
            "mode": "post" if job else "network_daily_cumulative"}

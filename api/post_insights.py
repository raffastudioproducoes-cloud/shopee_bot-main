"""Coleta auditável: somente IDs de posts confirmados em publish_jobs.

Nunca consulta /threads_insights (perfil), /{page}/insights (Página) nem
qualquer métrica geral de conta. Contadores de post são lifetime, não
eventos ocorridos dentro do filtro temporal da dashboard.
"""

import asyncio
import re
from datetime import datetime, timedelta, timezone

import httpx

from .crypto import decrypt
from .database import supabase
from .profiles import scope_account, scope_owner

TABLE = "publication_insights"
NETWORKS = ("threads", "facebook", "instagram", "tiktok", "x")
METRICS = ("views", "likes", "replies", "reposts", "quotes", "shares")
THREADS_HOST = "https://graph.threads.net/v1.0"
_EXTERNAL_ID = re.compile(r"^[0-9]{1,40}$")
_PAGE = 500
_PARALLEL = 4


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def parse_threads_post_insights(metrics):
    """Retorna somente contadores lifetime de um post; ausente não vira zero."""
    if not isinstance(metrics, list):
        return None
    result = {"views": None, "likes": None, "comments": None,
              "reposts": None, "shares": None, "quotes": None, "clicks": None}
    names = {"views": "views", "likes": "likes", "replies": "comments",
             "reposts": "reposts", "quotes": "quotes", "shares": "shares"}
    seen = set()
    for item in metrics:
        if not isinstance(item, dict) or item.get("name") not in names:
            continue
        name = item["name"]
        if name in seen:
            return None  # Não escolher arbitrariamente duplicatas conflitantes.
        seen.add(name)
        values = item.get("values")
        if isinstance(values, list) and len(values) == 1 and isinstance(values[0], dict):
            value = _count(values[0].get("value"))
        else:
            total = item.get("total_value")
            value = _count(total.get("value")) if isinstance(total, dict) else None
        result[names[name]] = value
    return result if seen and any(value is not None for value in result.values()) else None


def _profile_jobs(user_id, profile_id):
    """Trabalha apenas com publicações confirmadas e vinculadas a este perfil."""
    rows = []
    offset = 0
    since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    while True:
        page = (scope_owner(
            supabase.table("publish_jobs").select(
                "id,post_id,profile_id,network,external_id,finished_at"
            ), user_id, profile_id
        ).eq("network", "threads").eq("status", "succeeded")
         .gte("finished_at", since).order("finished_at", desc=True)
         .order("id").range(offset, offset + _PAGE - 1).execute()).data or []
        rows.extend(job for job in page if job.get("external_id"))
        if len(page) < _PAGE:
            break
        offset += _PAGE
    return rows


def _multi_part_ids(user_id, profile_id, jobs):
    parent_ids = list({job["post_id"] for job in jobs if job.get("post_id") is not None})
    if not parent_ids:
        return set()
    counts = {}
    for offset in range(0, len(parent_ids), _PAGE):
        part = parent_ids[offset:offset + _PAGE]
        rows = (scope_account(
            supabase.table("posts").select("id,post_id"), user_id
        ).in_("post_id", part).execute()).data or []
        for row in rows:
            counts[row["post_id"]] = counts.get(row["post_id"], 0) + 1
    return {post_id for post_id, count in counts.items() if count > 1}


def _threads_credential(user_id, profile_id):
    response = scope_owner(
        supabase.table("threads_credentials").select("t_user_id,access_token,status"),
        user_id, profile_id
    ).maybe_single().execute()
    data = response.data if response else None
    if not data or data.get("status") is not True or not data.get("t_user_id") or not data.get("access_token"):
        return None
    return data["access_token"]


async def read_threads_post(client, external_id, token):
    """A API oficial de mídia devolve totais do post, não insights da conta."""
    if not isinstance(external_id, str) or not _EXTERNAL_ID.fullmatch(external_id):
        return "invalid_id", None
    url = f"{THREADS_HOST}/{external_id}/insights"
    for metrics in (",".join(METRICS), "views"):
        try:
            response = await client.get(
                url, params={"metric": metrics},
                headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.RequestError:
            return "network_error", None
        if response.status_code in (401, 403):
            return "permission_required", None
        if response.status_code != 200:
            if response.status_code == 400 and metrics != "views":
                continue  # A Meta pode não oferecer alguma métrica para este tipo de mídia.
            return "api_error", None
        try:
            body = response.json()
        except ValueError:
            return "invalid_response", None
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            return "invalid_response", None
        values = parse_threads_post_insights(body["data"])
        return ("ok" if values is not None else "no_data"), values
    return "api_error", None


def _persist(job, user_id, state, metrics):
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "publish_job_id": job["id"], "user_id": user_id,
        "profile_id": job["profile_id"], "network": job["network"],
        "external_id": job["external_id"], "state": state,
        "last_attempt_at": now,
        "last_completed_at": now if state == "ok" else None,
        **{key: metrics.get(key) if metrics else None
           for key in ("views", "likes", "comments", "reposts", "shares", "quotes", "clicks")},
    }
    supabase.table(TABLE).upsert(payload, on_conflict="publish_job_id").execute()


async def collect_profile_posts(user_id, profile_id):
    """Usa a claim já existente do refresh; não adiciona agendador ou cron."""
    jobs = await asyncio.to_thread(_profile_jobs, user_id, profile_id)
    if not jobs:
        return {"threads": "no_posts", "facebook": "not_connected",
                "instagram": "not_connected", "tiktok": "unsupported", "x": "unsupported"}
    token_cipher = await asyncio.to_thread(_threads_credential, user_id, profile_id)
    if not token_cipher:
        return {"threads": "not_connected", "facebook": "not_connected",
                "instagram": "not_connected", "tiktok": "unsupported", "x": "unsupported"}
    try:
        token = decrypt(token_cipher)
    except Exception:
        return {"threads": "unavailable", "facebook": "not_connected",
                "instagram": "not_connected", "tiktok": "unsupported", "x": "unsupported"}
    multi = await asyncio.to_thread(_multi_part_ids, user_id, profile_id, jobs)
    semaphore = asyncio.Semaphore(_PARALLEL)

    async with httpx.AsyncClient(timeout=15) as client:
        async def collect(job):
            async with semaphore:
                if job["post_id"] in multi:
                    state, metrics = "multipart_unmapped", None
                else:
                    state, metrics = await read_threads_post(client, job["external_id"], token)
                await asyncio.to_thread(_persist, job, user_id, state, metrics)
                return state
        outcomes = await asyncio.gather(*(collect(job) for job in jobs), return_exceptions=True)
    states = [value if isinstance(value, str) else "unavailable" for value in outcomes]
    overall = "ok" if states and all(s == "ok" for s in states) else (
        "partial" if "ok" in states else states[0] if states else "no_posts"
    )
    return {"threads": overall, "facebook": "not_connected",
            "instagram": "not_connected", "tiktok": "unsupported", "x": "unsupported"}


def current_network_connections(user_id, profile_id=None):
    """Não se deixa enganar por estados antigos em analytics_daily_refreshes."""
    connections = {}
    tables = {
        "threads": ("threads_credentials", "t_user_id", "access_token"),
        "facebook": ("facebook_credentials", "page_id", "page_access_token"),
        "instagram": ("instagram_credentials", "ig_user_id", "user_access_token"),
    }
    for network, (table, identifier, token_field) in tables.items():
        query = scope_account(
            supabase.table(table).select(f"profile_id,{identifier},{token_field},status"), user_id
        ).eq("status", True)
        if profile_id:
            query = query.eq("profile_id", profile_id)
        rows = query.execute().data or []
        connections[network] = any(x.get(identifier) and x.get(token_field) for x in rows)
    return connections


def published_jobs(user_id, profile_id, days, network=None):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    offset = 0
    rows = []
    while True:
        query = scope_account(
            supabase.table("publish_jobs").select(
                "id,post_id,profile_id,network,external_id,finished_at"
            ), user_id
        ).eq("status", "succeeded").gte("finished_at", since)
        if profile_id:
            query = query.eq("profile_id", profile_id)
        if network:
            query = query.eq("network", network)
        page = (query.order("finished_at", desc=True).order("id")
                .range(offset, offset + _PAGE - 1).execute()).data or []
        rows.extend(page)
        if len(page) < _PAGE:
            return rows
        offset += _PAGE


def indexed_insights(user_id, jobs):
    ids = [job["id"] for job in jobs]
    index = {}
    for offset in range(0, len(ids), _PAGE):
        response = (scope_account(
            supabase.table(TABLE).select(
                "publish_job_id,network,external_id,state,views,likes,comments,reposts,"
                "shares,quotes,clicks,last_completed_at"
            ), user_id
        ).in_("publish_job_id", ids[offset:offset + _PAGE]).execute())
        for item in response.data or []:
            index[item["publish_job_id"]] = item
    return index


def distinct_published_jobs(jobs):
    """Um mesmo ID externo publicado/reconciliado duas vezes não duplica insights."""
    seen = set()
    result = []
    for job in jobs:
        identifier = job.get("external_id")
        if identifier:
            key = (job["network"], identifier)
            if key in seen:
                continue
            seen.add(key)
        result.append(job)
    return result


INSIGHT_FIELDS = ("views", "likes", "comments", "reposts", "shares", "quotes", "clicks")


def summarize_post_metrics(jobs, index):
    """Somente a interseção job confirmado + ID externo igual + coleta válida."""
    results = {field: None for field in INSIGHT_FIELDS}
    collected, eligible = 0, 0
    states = set()
    for job in distinct_published_jobs(jobs):
        external_id = job.get("external_id")
        if not external_id:
            continue
        eligible += 1
        item = index.get(job["id"])
        if not item or item.get("network") != job["network"] or item.get("external_id") != external_id:
            states.add("not_collected")
            continue
        states.add(item.get("state", "not_collected"))
        if item.get("state") != "ok":
            continue
        collected += 1
        for field in INSIGHT_FIELDS:
            value = _count(item.get(field))
            if value is not None:
                results[field] = (results[field] or 0) + value
    return results, collected, eligible, states

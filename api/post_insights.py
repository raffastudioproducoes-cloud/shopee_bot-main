"""Coleta auditável: somente IDs de posts confirmados em publish_jobs.

Nunca consulta /threads_insights (perfil), /{page}/insights (Página) nem
qualquer métrica geral de conta. Contadores de post são lifetime, não
eventos ocorridos dentro do filtro temporal da dashboard.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

from . import meta_post_insights as meta
from .crypto import decrypt
from .database import supabase
from .profiles import scope_account, scope_owner

logger = logging.getLogger(__name__)

TABLE = "publication_insights"
HISTORY_TABLE = "post_metrics"
NETWORKS = ("threads", "facebook", "instagram", "tiktok", "x", "shopee_video")
# Redes com coletor por post; TikTok, X e Shopee Vídeo ficam "unsupported" (fases seguintes).
COLLECTED_NETWORKS = ("threads", "instagram", "facebook")
SOURCES = {"threads": "threads_media_insights", "instagram": "ig_media_insights",
           "facebook": "fb_post_insights"}
METRICS = ("views", "likes", "replies", "reposts", "quotes", "shares")
THREADS_HOST = "https://graph.threads.net/v1.0"
_EXTERNAL_ID = re.compile(r"^[0-9]{1,40}$")
# Mesmo formato gravado pela confirmação manual (api/routers/posts.py::_valid_threads_permalink).
_PERMALINK = re.compile(r"https://(?:www\.)?threads\.(?:net|com)/@[A-Za-z0-9_.]{1,30}/post/([A-Za-z0-9_-]{4,70})/?")
_PAGE = 500
_PARALLEL = 4
_RESOLVE_PAGES = 5  # ponytail: 500 posts recentes; ampliar se houver confirmação manual mais antiga.
_WINDOWS = ((timedelta(hours=1), "1h"), (timedelta(hours=24), "24h"), (timedelta(days=7), "7d"),
            (timedelta(days=30), "30d"), (timedelta(days=90), "90d"))
SEQUENCE_LIMITATION = "sequencia: o publicador guarda apenas o ID da ultima parte"
FAN_COUNT_KEY = "facebook_fan_count"


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
        ).in_("network", list(COLLECTED_NETWORKS)).eq("status", "succeeded")
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
    # Qualquer resposta encadeada faz do post uma sequência (2 partes já têm 1 filho).
    return {post_id for post_id, count in counts.items() if count >= 1}


def _threads_account(user_id, profile_id):
    response = scope_owner(
        supabase.table("threads_credentials").select("t_user_id,access_token,status"),
        user_id, profile_id
    ).maybe_single().execute()
    data = response.data if response else None
    if not data or data.get("status") is not True or not data.get("t_user_id") or not data.get("access_token"):
        return None
    return str(data["t_user_id"]), data["access_token"]


def _threads_credential(user_id, profile_id):
    account = _threads_account(user_id, profile_id)
    return account[1] if account else None


def window_label(finished_at, now=None):
    """Idade do post na coleta: 1h/24h/7d/30d/90d; mais velho ou sem data = latest."""
    try:
        published = datetime.fromisoformat(str(finished_at).replace("Z", "+00:00"))
    except ValueError:
        return "latest"
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age = (now or datetime.now(timezone.utc)) - published
    return next((label for limit, label in _WINDOWS if age <= limit), "latest")


def permalink_code(value):
    match = _PERMALINK.fullmatch(value) if isinstance(value, str) else None
    return match.group(1) if match else None


async def resolve_permalinks(client, threads_user_id, token, codes):
    """Permalink (confirmação manual) -> ID de mídia, só entre os posts do próprio usuário."""
    found = {}
    if not codes or not _EXTERNAL_ID.fullmatch(str(threads_user_id or "")):
        return found
    url = f"{THREADS_HOST}/{threads_user_id}/threads"
    params = {"fields": "id,permalink", "limit": 100}
    for _ in range(_RESOLVE_PAGES):
        try:
            response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
            body = response.json() if response.status_code == 200 else None
        except (httpx.RequestError, ValueError):
            return found
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            return found
        for item in body["data"]:
            if not isinstance(item, dict):
                continue
            code, media_id = permalink_code(item.get("permalink")), item.get("id")
            if code in codes and isinstance(media_id, str) and _EXTERNAL_ID.fullmatch(media_id):
                found[code] = media_id
        after = ((body.get("paging") or {}).get("cursors") or {}).get("after")
        if len(found) == len(codes) or not isinstance(after, str) or not after:
            return found
        params = {**params, "after": after}
    return found


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
           for key in ("views", "reach", "likes", "comments", "reposts", "shares", "saves",
                       "quotes", "clicks")},
    }
    supabase.table(TABLE).upsert(payload, on_conflict="publish_job_id").execute()


def combined_shares(metrics):
    """Compartilhamentos + reposts; NULL só quando a rede não forneceu nenhum dos dois."""
    values = [metrics.get(key) for key in ("shares", "reposts")] if metrics else []
    present = [value for value in values if isinstance(value, int) and value >= 0]
    return sum(present) if present else None


def history_row(job, user_id, status, metrics, measured_id=None, extra=None):
    metrics = metrics or {}
    detail = {key: metrics.get(key) for key in ("reposts", "quotes") if metrics.get(key) is not None}
    if metrics.get("shares") is not None:
        detail["network_shares"] = metrics["shares"]
    ok = status in ("ok", "parcial")
    return {
        "user_id": user_id, "profile_id": job.get("profile_id"), "post_id": job.get("post_id"),
        "publish_job_id": job["id"], "network": job["network"],
        "external_id": str(measured_id or job.get("external_id") or "")[:512] or None,
        "window_label": window_label(job.get("finished_at")),
        "views": metrics.get("views"), "reach": metrics.get("reach"), "likes": metrics.get("likes"),
        "comments": metrics.get("comments"), "shares": combined_shares(metrics),
        # Nenhuma rede dá clique em link por post aqui; cliques vêm do redirecionador.
        "saves": metrics.get("saves"), "clicks": None,
        "extra": {**detail, **(extra or {})}, "source": SOURCES.get(job["network"]),
        "status": status, "error": None if ok else status[:200],
    }


def _record_history(row):
    """Append-only; falha aqui nunca derruba a coleta nem o upsert legado."""
    try:
        supabase.table(HISTORY_TABLE).insert(row).execute()
    except Exception:
        logger.warning("Histórico de métricas indisponível nesta coleta")


def _overall(states):
    if not states:
        return "no_posts"
    if all(state == "ok" for state in states):
        return "ok"
    return "partial" if "ok" in states else states[0]


async def _collect_threads(client, user_id, profile_id, jobs):
    account = await asyncio.to_thread(_threads_account, user_id, profile_id)
    if not account:
        return "not_connected"
    threads_user_id, token_cipher = account
    try:
        token = decrypt(token_cipher)
    except Exception:
        return "unavailable"
    multi = await asyncio.to_thread(_multi_part_ids, user_id, profile_id, jobs)
    semaphore = asyncio.Semaphore(_PARALLEL)
    codes = {code for code in (permalink_code(job["external_id"]) for job in jobs) if code}
    resolved = await resolve_permalinks(client, threads_user_id, token, codes)

    async def collect(job):
        async with semaphore:
            code = permalink_code(job["external_id"])
            measured_id = resolved.get(code) if code else job["external_id"]
            extra = {"resolved_from": "permalink"} if code else {}
            if code and not measured_id:
                state, metrics = "sem_id", None
            else:
                state, metrics = await read_threads_post(client, measured_id, token)
            status = state
            if job["post_id"] in multi:
                # Só o ID da última parte existe: mede essa parte e marca parcial.
                extra.update(parts_measured=1, limitation=SEQUENCE_LIMITATION)
                status = "parcial" if state == "ok" else state
                state = "multipart_unmapped"
            await asyncio.to_thread(_persist, job, user_id, state, metrics)
            await asyncio.to_thread(_record_history, history_row(
                job, user_id, status, metrics, measured_id, extra))
            return state
    outcomes = await asyncio.gather(*(collect(job) for job in jobs), return_exceptions=True)
    return _overall([value if isinstance(value, str) else "unavailable" for value in outcomes])


def _meta_account(network, user_id, profile_id):
    """Token cifrado da conta conectada: usuário (Instagram) ou Página (Facebook)."""
    table, identifier, token_field = {
        "instagram": ("instagram_credentials", "ig_user_id", "user_access_token"),
        "facebook": ("facebook_credentials", "page_id", "page_access_token"),
    }[network]
    response = scope_owner(
        supabase.table(table).select(f"{identifier},{token_field},status"), user_id, profile_id
    ).maybe_single().execute()
    data = response.data if response else None
    if not data or data.get("status") is not True or not data.get(identifier) or not data.get(token_field):
        return None
    return str(data[identifier]), data[token_field]


async def _collect_meta(client, network, user_id, profile_id, jobs, audience_out=None):
    """Instagram/Facebook: falha por post é registrada e o restante segue.

    Escopo ausente, token expirado ou rate limit valem para a conta inteira: o primeiro
    post que recebe um deles para as chamadas seguintes (sem retry; a próxima rodada
    tenta de novo). Posts não consultados por rate limit mantêm o último valor.
    """
    account = await asyncio.to_thread(_meta_account, network, user_id, profile_id)
    if not account:
        return "not_connected"
    account_id, token_cipher = account
    try:
        token = decrypt(token_cipher)
    except Exception:
        return "unavailable"
    reader = meta.read_instagram_media if network == "instagram" else meta.read_facebook_post
    # Uma leitura de curtidas por conta e rodada; falha = None e a coleta segue igual.
    audience = await meta.read_page_audience(client, account_id, token) if network == "facebook" else None
    if audience and audience_out is not None:
        audience_out.update(audience)
    semaphore = asyncio.Semaphore(_PARALLEL)
    stopped = []

    async def collect(job):
        async with semaphore:
            if stopped:
                state, metrics, extra = stopped[0], None, {"skipped": True}
            else:
                state, metrics, extra = await reader(client, job["external_id"], token)
                state = meta.classify_page_audience(state, audience)
                if state in meta.STOP_STATES and not stopped:
                    stopped.append(state)
            if audience:
                extra["page_fan_count"] = audience["fan_count"]
            measured_id = extra.pop("measured_id", None)
            if state != "rate_limited":
                await asyncio.to_thread(_persist, job, user_id, state, metrics)
            await asyncio.to_thread(_record_history, history_row(
                job, user_id, state, metrics, measured_id, extra))
            return state
    outcomes = await asyncio.gather(*(collect(job) for job in jobs), return_exceptions=True)
    return _overall([value if isinstance(value, str) else "unavailable" for value in outcomes])


async def _guarded(network, coroutine):
    """Uma rede quebrada nunca derruba a coleta das outras nem a rotina."""
    try:
        return await coroutine
    except Exception as err:
        logger.warning("Coleta de métricas %s falhou: %s", network, type(err).__name__)
        return "unavailable"


async def collect_profile_posts(user_id, profile_id):
    """Usa a claim já existente do refresh; não adiciona agendador ou cron."""
    jobs = await asyncio.to_thread(_profile_jobs, user_id, profile_id)
    states = {"threads": "no_posts", "facebook": "no_posts", "instagram": "no_posts",
              "tiktok": "unsupported", "x": "unsupported", "shopee_video": "unsupported"}
    by_network = {network: [job for job in jobs if job.get("network") == network]
                  for network in COLLECTED_NETWORKS}
    audience = {}
    async with httpx.AsyncClient(timeout=15) as client:
        for network, subset in by_network.items():
            if not subset:
                continue
            work = (_collect_threads(client, user_id, profile_id, subset) if network == "threads"
                    else _collect_meta(client, network, user_id, profile_id, subset, audience))
            states[network] = await _guarded(network, work)
    if "fan_count" in audience:
        # Vai para analytics_daily_refreshes.provider_states (JSON existente, sem migração).
        states[FAN_COUNT_KEY] = audience["fan_count"]
    return states


def facebook_fan_counts(user_id, profile_id=None):
    """profile_id -> curtidas da Página na última coleta. Falha de leitura = {} (só some o N do texto)."""
    try:
        query = scope_account(
            supabase.table("analytics_daily_refreshes").select("profile_id,provider_states"), user_id)
        if profile_id:
            query = query.eq("profile_id", profile_id)
        rows = query.execute().data or []
    except Exception:
        logger.warning("Curtidas da Página indisponíveis para a tela de análises")
        return {}
    counts = {}
    for row in rows:
        states = row.get("provider_states")
        value = _count(states.get(FAN_COUNT_KEY)) if isinstance(states, dict) else None
        if value is not None:
            counts[row.get("profile_id")] = value
    return counts


def shared_fan_count(counts, profile_ids):
    """N só quando todas as Páginas consultadas têm o mesmo número; senão None (texto sem N)."""
    values = {counts[p] for p in profile_ids if p in counts}
    return values.pop() if len(values) == 1 else None


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
                "publish_job_id,network,external_id,state,views,reach,likes,comments,reposts,"
                "shares,saves,quotes,clicks,last_completed_at"
            ), user_id
        ).in_("publish_job_id", ids[offset:offset + _PAGE]).execute())
        for item in response.data or []:
            index[item["publish_job_id"]] = item
    return index


WATCH_TIME_NETWORKS = ("instagram", "facebook")
_WATCH_ROWS_PER_JOB = 50  # ponytail: últimas coletas por envio; RPC SQL se o histórico crescer muito.


def latest_watch_times(user_id, jobs):
    """{publish_job_id: ms} do tempo médio assistido mais recente (post_metrics.extra).

    Só Instagram/Facebook fornecem; sem valor o job fica de fora (a UI mostra "—")."""
    ids = [job["id"] for job in jobs if job.get("network") in WATCH_TIME_NETWORKS]
    latest = {}
    for offset in range(0, len(ids), _PAGE):
        chunk = ids[offset:offset + _PAGE]
        rows = (scope_account(
            supabase.table(HISTORY_TABLE).select("publish_job_id,extra,collected_at"), user_id
        ).in_("publish_job_id", chunk).eq("status", "ok").order("collected_at", desc=True)
            .limit(len(chunk) * _WATCH_ROWS_PER_JOB).execute()).data or []
        for row in rows:
            value = _count((row.get("extra") or {}).get("avg_watch_time_ms"))
            if value is None:
                continue
            job_id, when = row["publish_job_id"], str(row.get("collected_at") or "")
            if job_id not in latest or when > latest[job_id][0]:
                latest[job_id] = (when, value)
    return {job_id: value for job_id, (_, value) in latest.items()}


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

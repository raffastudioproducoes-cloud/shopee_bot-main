"""Coleta diária e manual de insights, com claim compartilhado no PostgreSQL.

Métricas de jobs são calculadas ao ler /analytics/summary. Este módulo só
armazena leituras de provedores, sem tokens, corpos de erro ou dados de posts.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from apis.meta_version import GRAPH_URL, GRAPH_VERSION
from .crypto import decrypt
from .database import supabase
from .profiles import scope_owner

logger = logging.getLogger(__name__)
TABLE = "analytics_daily_refreshes"
PROBES = {
    "threads": ("threads_credentials", "t_user_id", "access_token", "views", None),
    "facebook": ("facebook_credentials", "page_id", "page_access_token", "page_media_view", "day"),
    "instagram": ("instagram_credentials", "ig_user_id", "user_access_token", "reach", "day"),
}


def _safe_nonnegative_int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _facebook_daily_values(metrics):
    """Somente contagens diárias explicitamente validadas, sem somar dias faltantes."""
    counts = {}
    if not isinstance(metrics, list):
        return None
    for metric in metrics:
        if not isinstance(metric, dict) or metric.get("name") != "page_media_view":
            return None
        values = metric.get("values")
        if not isinstance(values, list):
            return None
        for item in values:
            if not isinstance(item, dict):
                return None
            value = _safe_nonnegative_int(item.get("value"))
            end_time = item.get("end_time")
            if value is None or not isinstance(end_time, str):
                return None
            try:
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                return None
            if end.tzinfo is None:
                return None
            counts[end.astimezone(timezone.utc).date().isoformat()] = value
    return [{"period_end": day, "value": counts[day]} for day in sorted(counts)]


def _threads_views(metrics):
    """Não somar pontos de uma série nem presumir que result_count são views."""
    if not isinstance(metrics, list) or len(metrics) != 1:
        return None
    metric = metrics[0]
    if not isinstance(metric, dict) or metric.get("name") != "views":
        return None
    total = metric.get("total_value")
    if isinstance(total, dict):
        return _safe_nonnegative_int(total.get("value"))
    values = metric.get("values")
    if isinstance(values, list) and len(values) == 1 and isinstance(values[0], dict):
        return _safe_nonnegative_int(values[0].get("value"))
    return None


def _credential(user_id, profile_id, network):
    table, id_col, token_col, _, _ = PROBES[network]
    row = scope_owner(
        supabase.table(table).select(f"{id_col},{token_col}"),
        user_id, profile_id,
    ).maybe_single().execute()
    data = row.data if row else None
    if not data or not data.get(id_col) or not data.get(token_col):
        return None
    return data[id_col], data[token_col]


async def _fetch_network(user_id, profile_id, network):
    try:
        credential = await asyncio.to_thread(_credential, user_id, profile_id, network)
        if credential is None:
            return {"state": "not_connected"}
        identifier, ciphertext = credential
        _, _, _, metric, period = PROBES[network]
        params = {"metric": metric}
        if period:
            params["period"] = period
        if network == "facebook":
            today = datetime.now(timezone.utc).date()
            params["since"] = (today - timedelta(days=89)).isoformat()
            params["until"] = (today + timedelta(days=1)).isoformat()
        host = "https://graph.threads.net/v1.0" if network == "threads" else f"{GRAPH_URL}/{GRAPH_VERSION}"
        endpoint = "threads_insights" if network == "threads" else "insights"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{host}/{identifier}/{endpoint}",
                params=params,
                headers={"Authorization": f"Bearer {decrypt(ciphertext)}"},
            )
        if response.status_code != 200:
            return {"state": "api_error"}
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            return {"state": "invalid_response"}
        metrics = body["data"]
        if network == "facebook":
            daily = _facebook_daily_values(metrics)
            if daily is None:
                return {"state": "invalid_response"}
            return {"state": "ok" if daily else "no_data", "daily": daily}
        if network == "threads":
            views = _threads_views(metrics)
            return {"state": "ok" if views is not None else "no_data", "views": views}
        # Instagram devolve reach, não visualizações; preservar a distinção.
        return {"state": "ok" if metrics else "no_data"}
    except httpx.RequestError:
        return {"state": "network_error"}
    except (ValueError, TypeError, KeyError):
        return {"state": "invalid_response"}
    except Exception:
        logger.exception("Falha interna sanitizada ao consultar insights (%s)", network)
        return {"state": "unavailable"}


def _claim(user_id, profile_id, manual):
    seconds = 300 if manual else 86400
    result = supabase.rpc("claim_analytics_refresh", {
        "p_user_id": str(user_id), "p_profile_id": str(profile_id),
        "p_min_seconds": seconds,
    }).execute()
    return result.data if result else None


async def refresh_account(user_id, profile_id, *, manual=False):
    """Retorna estado seguro. Nunca realiza nova coleta sem adquirir o claim."""
    if not profile_id:
        return {"state": "no_profile"}
    token = await asyncio.to_thread(_claim, user_id, profile_id, manual)
    if not token:
        return {"state": "recent"}
    network_results = await asyncio.gather(
        *(_fetch_network(user_id, profile_id, name) for name in PROBES)
    )
    results = dict(zip(PROBES, network_results))
    states = {name: value["state"] for name, value in results.items()}
    now = datetime.now(timezone.utc).isoformat()
    facebook = results["facebook"]
    threads = results["threads"]
    # Snapshot atômico por claim: um worker atrasado não reescreve outro.
    payload = {
        "last_completed_at": now,
        "locked_until": None,
        "claim_token": None,
        "provider_states": states,
        "facebook_daily_values": facebook.get("daily") if facebook["state"] == "ok" else [],
        "threads_views": threads.get("views") if threads["state"] == "ok" else None,
        "metrics_collected_at": now if "ok" in states.values() else None,
    }
    await asyncio.to_thread(
        lambda: supabase.table(TABLE).update(payload)
        .eq("user_id", user_id).eq("profile_id", profile_id)
        .eq("claim_token", token).execute()
    )
    return {"state": "updated", "provider_states": states}


def _due_profiles(limit=12):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = (supabase.table(TABLE).select("user_id,profile_id")
            .lt("last_attempt_at", cutoff).order("last_attempt_at")
            .limit(limit).execute())
    return rows.data or []


def refresh_due_analytics():
    """Chamado pelo APScheduler; reprocessa atrasados após cold starts do Render."""
    try:
        rows = _due_profiles()
    except Exception:
        logger.exception("Não foi possível listar insights diários vencidos")
        return
    for row in rows:
        try:
            asyncio.run(refresh_account(row["user_id"], row["profile_id"]))
        except Exception:
            logger.exception("Falha isolada na rotina diária de analytics")

"""Atualiza exclusivamente insights de posts enviados pelo Auto Orbital.

O claim e o agendamento existentes são reutilizados. Nunca consulta insights
gerais de conta, perfil ou Página e invalida snapshots legados dessa origem.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .database import supabase
from .post_insights import collect_profile_posts

logger = logging.getLogger(__name__)
TABLE = "analytics_daily_refreshes"


def _claim(user_id, profile_id, manual):
    seconds = 300 if manual else 86400
    result = supabase.rpc("claim_analytics_refresh", {
        "p_user_id": str(user_id), "p_profile_id": str(profile_id),
        "p_min_seconds": seconds,
    }).execute()
    return result.data if result else None


async def refresh_account(user_id, profile_id, *, manual=False):
    if not profile_id:
        return {"state": "no_profile"}
    token = await asyncio.to_thread(_claim, user_id, profile_id, manual)
    if not token:
        return {"state": "recent"}
    try:
        states = await collect_profile_posts(user_id, profile_id)
    except Exception:
        logger.exception("Falha sanitizada na coleta por publicação")
        states = {"threads": "unavailable", "facebook": "not_connected",
                  "instagram": "not_connected", "tiktok": "unsupported", "x": "unsupported"}
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "last_completed_at": now,
        "locked_until": None,
        "claim_token": None,
        "provider_states": states,
        # Nunca oferecer snapshots antigos de métricas de conta ou Página.
        "facebook_daily_values": [],
        "threads_views": None,
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
    """Executado pelo APScheduler já instalado, sem novo cron no Supabase."""
    try:
        rows = _due_profiles()
    except Exception:
        logger.exception("Não foi possível listar insights vencidos")
        return
    for row in rows:
        try:
            asyncio.run(refresh_account(row["user_id"], row["profile_id"]))
        except Exception:
            logger.exception("Falha isolada na rotina diária de analytics")

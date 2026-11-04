"""F4D: leitura de plano/uso; nunca reserva cota nem cria publicações.

A política/ownership é verificada em cada leitura. Contagens exatas são
independentes de paginação; ausência/falha nunca é transformada em zero.
"""
import os

from fastapi import HTTPException

from .database import supabase
from .campaign_policy import load_campaign_policy, campaign_limits_response

LIMIT_FIELDS = {
    "products": "products_per_account",
    "lists": "lists_per_profile",
    "profiles": "max_profiles_per_account",
    "immediate": "immediate_per_hour",
    "recurring": "recurring_slots_per_day",
}


def _count(table, user_id, profile_id=None):
    try:
        query = supabase.table(table).select("id", count="exact", head=True).eq("user_id", user_id)
        if profile_id is not None:
            query = query.eq("profile_id", profile_id)
        if table == "profiles" and os.getenv("PROFILE_ARCHIVAL_ENABLED", "false").lower() == "true":
            query = query.is_("archived_at", "null")
        result = query.execute()
        count = getattr(result, "count", None)
        return count if type(count) is int and count >= 0 else None
    except Exception:
        return None


def account_usage_response(user_id: str, profile_id: str) -> dict:
    policy = load_campaign_policy(user_id, profile_id)
    limits = {}
    if not policy.is_admin:
        try:
            result = (supabase.table("plan_limits").select(",".join(LIMIT_FIELDS.values()))
                      .eq("tier", policy.tier).maybe_single().execute())
            row = result.data if result else None
            if (not isinstance(row, dict) or any(
                    type(row.get(field)) is not int or row[field] < 0
                    for field in LIMIT_FIELDS.values())):
                raise ValueError("invalid policy")
            limits = {key: row[field] for key, field in LIMIT_FIELDS.items()}
        except Exception:
            raise HTTPException(status_code=503, detail="Limites do plano indisponíveis. Tente novamente.") from None

    usage = {
        "products": _count("products", user_id),
        "lists": _count("product_lists", user_id, profile_id),
        "profiles": _count("profiles", user_id),
        # A união de reservas 073 e legado exige leitura transacional própria.
        # Não deduzir consumo pela página de posts nem apenas pelas reservas.
        "immediate": None,
        "recurring": None,
    }
    return {
        **campaign_limits_response(policy, profile_id),
        "resources": {
            key: {
                "used": used,
                "limit": None if policy.is_admin else limits[key],
                "unlimited": policy.is_admin,
                "usage_status": "available" if used is not None else "unavailable",
            } for key, used in usage.items()
        },
    }

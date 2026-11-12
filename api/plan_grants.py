"""Concessão de plano pelo ADMIN (Pro/Premium por prazo) e volta automática ao Free.

A concessão grava `users.plan_tier` (autoridade comercial) e `users.campaign_paid_through`
(campanhas exigem período pago vigente) e deixa o rastro em `plan_grants`. Quem concedeu,
quando e até quando ficam na tabela; remover o plano ("free") encerra a concessão ativa.
A expiração é uma varredura periódica (`expire_due_grants`, chamada pelo loop do `main.py`).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

from .audit_trail import record_audit_event
from .database import supabase

MIN_DAYS = 1
MAX_DAYS = 365
_EXPIRE_BATCH = 100


class PlanGrantRequest(BaseModel):
    plan: Literal["free", "pro", "premium"]
    days: int | None = Field(None, ge=MIN_DAYS, le=MAX_DAYS)
    ends_at: datetime | None = None
    reason: str | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def _duration_matches_plan(self):
        if self.plan == "free":
            if self.days is not None or self.ends_at is not None:
                raise ValueError("Remover o plano não aceita duração")
        elif (self.days is None) == (self.ends_at is None):
            raise ValueError("Informe days ou ends_at (apenas um)")
        return self


def resolve_expiry(req: PlanGrantRequest, now: datetime) -> datetime:
    """Fim da concessão em UTC; `ends_at` sem fuso é tratado como UTC."""
    if req.days is not None:
        return now + timedelta(days=req.days)
    ends = req.ends_at if req.ends_at.tzinfo else req.ends_at.replace(tzinfo=timezone.utc)
    ends = ends.astimezone(timezone.utc)
    if ends <= now:
        raise HTTPException(status_code=422, detail="A data final deve estar no futuro.")
    if ends > now + timedelta(days=MAX_DAYS):
        raise HTTPException(status_code=422, detail=f"A duração máxima é de {MAX_DAYS} dias.")
    return ends


def _rows(result) -> list[dict]:
    return (result.data if result else None) or []


def _target(user_id: str) -> dict:
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Usuário não encontrado") from None
    rows = _rows(supabase.table("users").select("id,access,plan_tier,campaign_paid_through")
                 .eq("id", user_id).limit(1).execute())
    if not rows:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if rows[0].get("access") == "ADMIN":
        raise HTTPException(status_code=400, detail="Contas ADMIN não têm plano.")
    return rows[0]


def _has_open_subscription(user_id: str) -> bool:
    return bool(_rows(supabase.table("billing_subscriptions").select("id").eq("user_id", user_id)
                      .in_("status", ["active", "overdue"]).limit(1).execute()))


def apply_plan(admin_id: str, user_id: str, req: PlanGrantRequest) -> dict:
    now = datetime.now(timezone.utc)
    target = _target(user_id)
    if _has_open_subscription(user_id):
        raise HTTPException(status_code=409, detail="A conta tem assinatura ativa; altere o plano pela cobrança.")
    before = {"plan_tier": target.get("plan_tier"), "plan_expires_at": target.get("campaign_paid_through")}
    ended = {"status": "revoked", "ended_at": now.isoformat(), "ended_by": admin_id}

    if req.plan == "free":
        supabase.table("plan_grants").update(ended).eq("user_id", user_id).eq("status", "active").execute()
        supabase.table("users").update({"plan_tier": "free", "campaign_paid_through": None}).eq("id", user_id).execute()
        result = {"user_id": user_id, "plan_tier": "free", "plan_expires_at": None, "grant_id": None}
    else:
        expires = resolve_expiry(req, now)
        supabase.table("plan_grants").update({**ended, "status": "superseded"}) \
            .eq("user_id", user_id).eq("status", "active").execute()
        grant = _rows(supabase.table("plan_grants").insert({
            "user_id": user_id, "tier": req.plan, "previous_tier": before["plan_tier"], "granted_by": admin_id,
            "granted_at": now.isoformat(), "expires_at": expires.isoformat(), "reason": req.reason,
        }).execute())
        if not grant:
            raise HTTPException(status_code=500, detail="Falha ao registrar a concessão.")
        try:
            supabase.table("users").update({"plan_tier": req.plan, "campaign_paid_through": expires.isoformat()}) \
                .eq("id", user_id).execute()
        except Exception:
            supabase.table("plan_grants").update(ended).eq("id", grant[0]["id"]).execute()
            raise
        result = {"user_id": user_id, "plan_tier": req.plan, "plan_expires_at": expires.isoformat(),
                  "grant_id": grant[0]["id"]}

    record_audit_event("user_plan", user_id, admin_id, "plan_grant" if req.plan != "free" else "plan_remove",
                       before, {"plan_tier": result["plan_tier"], "plan_expires_at": result["plan_expires_at"]})
    return result


def expire_due_grants(now: datetime | None = None) -> int:
    """Concessões vencidas voltam a conta ao Free. Idempotente e segura entre workers."""
    now_iso = (now or datetime.now(timezone.utc)).isoformat()
    due = _rows(supabase.table("plan_grants").select("id,user_id,tier").eq("status", "active")
                .lte("expires_at", now_iso).limit(_EXPIRE_BATCH).execute())
    for grant in due:
        # Só derruba se o plano ainda é o desta concessão e o período já passou.
        supabase.table("users").update({"plan_tier": "free", "campaign_paid_through": None}) \
            .eq("id", grant["user_id"]).eq("plan_tier", grant["tier"]).lte("campaign_paid_through", now_iso).execute()
        supabase.table("plan_grants").update({"status": "expired", "ended_at": now_iso}) \
            .eq("id", grant["id"]).eq("status", "active").execute()
    return len(due)

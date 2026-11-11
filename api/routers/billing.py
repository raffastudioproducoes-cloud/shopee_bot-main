"""Cobrança com Asaas — fase 1: tabela de preços e recebimento do webhook.

O webhook só confere o token, grava o evento (idempotente pelo id) e responde
200; o processamento (ativar plano, atraso, estorno) entra na fase 3. O
navegador nunca altera plano: só o processador do webhook fará isso.
"""
from __future__ import annotations

import hmac
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import asaas_client, billing_events, billing_pricing
from ..account_identity import purchase_readiness
from ..config import settings
from ..crypto import decrypt
from ..database import supabase
from .auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])
MAX_WEBHOOK_BYTES = 256 * 1024
CHECKOUT_MINUTES = 60
MAX_CHECKOUTS_PER_HOUR = 5
OPEN_SUBSCRIPTION = ("pending", "active", "overdue")
TIER_NAMES = {"pro": "Pro", "premium": "Premium"}
PERIOD_NAMES = {"monthly": "mensal", "quarterly": "3 meses", "semiannual": "6 meses", "yearly": "1 ano"}
BRT = ZoneInfo("America/Sao_Paulo")


class CheckoutRequest(BaseModel):
    tier: Literal["pro", "premium"]
    period: Literal["monthly", "quarterly", "semiannual", "yearly"]
    billing_type: Literal["CREDIT_CARD", "PIX"]


@router.get("/plans")
async def list_plan_prices():
    """Preços calculados no servidor para Pro e Premium em cada período."""
    return {"currency": "BRL", "prices": billing_pricing.price_table(supabase)}


@router.post("/webhook/asaas")
async def asaas_webhook(request: Request, background: BackgroundTasks):
    expected = settings.asaas_webhook_token or ""
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook de cobrança não configurado")
    received = request.headers.get("asaas-access-token") or ""
    if not hmac.compare_digest(received.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Token inválido")
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Evento grande demais")
    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="JSON inválido") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Evento sem id ou tipo")
    event_id, event_type = payload.get("id"), payload.get("event")
    if not isinstance(event_id, str) or not event_id or not isinstance(event_type, str) or not event_type:
        raise HTTPException(status_code=400, detail="Evento sem id ou tipo")
    try:
        supabase.table("billing_webhook_events").upsert(
            {"environment": asaas_client.environment(), "event_id": event_id[:200],
             "event_type": event_type[:100], "payload": payload},
            on_conflict="environment,event_id", ignore_duplicates=True,
        ).execute()
    except Exception as exc:
        # Sem gravar não respondemos 200: o Asaas tenta de novo depois.
        logger.error("Falha ao gravar evento de cobrança: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Tente novamente") from None
    # Aplica fora da resposta; o agendador repete o que falhar.
    background.add_task(billing_events.run_billing_jobs)
    return {"received": True}


def _one(result):
    # postgrest-py pode devolver None para maybe_single() sem linha.
    return (result.data if result is not None else None) or None


def _customer_id(user_id: str, user: dict, identity: dict, env: str) -> str:
    found = _one(supabase.table("billing_customers").select("asaas_customer_id")
                 .eq("user_id", user_id).eq("environment", env).maybe_single().execute())
    if found:
        return found["asaas_customer_id"]
    phone = re.sub(r"\D", "", identity.get("mobile_phone") or "")
    if phone.startswith("55") and len(phone) in (12, 13):
        phone = phone[2:]
    created = asaas_client.create_customer(
        name=identity["full_name"], cpf_cnpj=decrypt(identity["cpf_ciphertext"]),
        email=user["email"], mobile_phone=phone or None, external_reference=str(user_id))
    supabase.table("billing_customers").upsert(
        {"user_id": user_id, "environment": env, "asaas_customer_id": created["id"]},
        on_conflict="user_id,environment").execute()
    return created["id"]


@router.post("/checkout")
def create_checkout(body: CheckoutRequest, user_id: str = Depends(get_current_user_id)):
    """Cria o checkout recorrente do Asaas e devolve o link de pagamento.

    Não altera o plano: a ativação só acontece pelo webhook de pagamento.
    """
    if not asaas_client.enabled():
        raise HTTPException(503, "Contratação indisponível no momento.")
    env = asaas_client.environment()
    if not asaas_client.may_bill(user_id):
        raise HTTPException(403, "Contratação em fase de testes. Disponível em breve.")
    user = _one(supabase.table("users").select("id,email").eq("id", user_id).maybe_single().execute())
    if not user:
        raise HTTPException(404, "Conta não encontrada.")
    identity = _one(supabase.table("account_billing_identity").select("*")
                    .eq("user_id", user_id).maybe_single().execute()) or {}
    readiness = purchase_readiness(user, identity)
    if not readiness["ready"]:
        raise HTTPException(422, {"message": "Complete os dados da conta antes de assinar: "
                                             + ", ".join(readiness["missing"]) + ".",
                                  "missing": readiness["missing"]})
    open_subs = (supabase.table("billing_subscriptions").select("id").eq("user_id", user_id)
                 .eq("environment", env).in_("status", list(OPEN_SUBSCRIPTION)).limit(1).execute().data)
    if open_subs:
        raise HTTPException(409, "Sua conta já tem uma assinatura. Use a troca de plano.")
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent = (supabase.table("billing_checkouts").select("id").eq("user_id", user_id)
              .gte("created_at", since).limit(MAX_CHECKOUTS_PER_HOUR).execute().data or [])
    if len(recent) >= MAX_CHECKOUTS_PER_HOUR:
        raise HTTPException(429, "Muitas tentativas. Tente de novo em alguns minutos.")
    price = billing_pricing.quote(supabase, body.tier, body.period)
    order = supabase.table("billing_checkouts").insert({
        "user_id": user_id, "environment": env, "tier": body.tier, "period": body.period,
        "billing_type": body.billing_type, "value_cents": price["total_cents"],
    }).execute().data[0]
    base = settings.frontend_url.rstrip("/")
    try:
        customer = _customer_id(user_id, user, identity, env)
        created = asaas_client.create_checkout({
            "customer": customer,
            "billingTypes": [body.billing_type],
            "chargeTypes": ["RECURRENT"],
            "minutesToExpire": CHECKOUT_MINUTES,
            "externalReference": order["id"],
            "callback": {
                "successUrl": f"{base}/settings?assinatura=sucesso#planos",
                "cancelUrl": f"{base}/settings?assinatura=cancelada#planos",
                "expiredUrl": f"{base}/settings?assinatura=expirada#planos",
            },
            "items": [{
                "name": f"Auto Orbital {TIER_NAMES[body.tier]}",
                "description": f"Plano {TIER_NAMES[body.tier]} · {PERIOD_NAMES[body.period]}",
                "quantity": 1, "value": price["total_cents"] / 100,
            }],
            "subscription": {
                "cycle": price["cycle"],
                "nextDueDate": datetime.now(BRT).strftime("%Y-%m-%d %H:%M:%S"),
            },
        })
    except asaas_client.AsaasUnavailable:
        supabase.table("billing_checkouts").update({"status": "failed"}).eq("id", order["id"]).execute()
        raise HTTPException(503, "Pagamento indisponível no momento. Tente novamente.") from None
    except asaas_client.AsaasError as exc:
        supabase.table("billing_checkouts").update({"status": "failed"}).eq("id", order["id"]).execute()
        raise HTTPException(422, {"message": "O Asaas recusou os dados de cobrança.",
                                  "details": exc.messages[:3]}) from None
    supabase.table("billing_checkouts").update(
        {"asaas_checkout_id": created["id"], "status": "active"}).eq("id", order["id"]).execute()
    return {"checkout_url": asaas_client.checkout_url(created["id"]),
            "expires_in_minutes": CHECKOUT_MINUTES, "value_cents": price["total_cents"]}

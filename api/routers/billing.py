"""Cobrança com Asaas — fase 1: tabela de preços e recebimento do webhook.

O webhook só confere o token, grava o evento (idempotente pelo id) e responde
200; o processamento (ativar plano, atraso, estorno) entra na fase 3. O
navegador nunca altera plano: só o processador do webhook fará isso.
"""
from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, HTTPException, Request

from .. import asaas_client, billing_pricing
from ..config import settings
from ..database import supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])
MAX_WEBHOOK_BYTES = 256 * 1024


@router.get("/plans")
async def list_plan_prices():
    """Preços calculados no servidor para Pro e Premium em cada período."""
    return {"currency": "BRL", "prices": billing_pricing.price_table(supabase)}


@router.post("/webhook/asaas")
async def asaas_webhook(request: Request):
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
    return {"received": True}

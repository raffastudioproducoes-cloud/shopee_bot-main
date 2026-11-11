"""Processamento dos eventos de webhook do Asaas (fase 3).

Os eventos já estão gravados em `billing_webhook_events` pelo webhook. Aqui
eles são aplicados em ordem de chegada, um a um, e marcados como processados.
Só este módulo altera `users.plan_tier` por causa de cobrança.

Regras (decisões de Rafa):
- pagamento confirmado → plano ativo até o fim do período pago;
- atraso → até 15 dias de tolerância com o plano ativo; depois volta a Free;
- estorno ou chargeback → volta a Free na hora;
- assinatura cancelada → mantém o plano até o fim do período já pago.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from . import asaas_client, billing_pricing
from .database import supabase

logger = logging.getLogger(__name__)

GRACE_DAYS = 15
MAX_ATTEMPTS = 8
PAID_EVENTS = {"PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"}
REVERSAL_EVENTS = {"PAYMENT_REFUNDED", "PAYMENT_CHARGEBACK_REQUESTED", "PAYMENT_CHARGEBACK_DISPUTE"}
PAYMENT_RECORD_EVENTS = {"PAYMENT_CREATED", "PAYMENT_UPDATED", "PAYMENT_DELETED", "PAYMENT_RESTORED",
                         "PAYMENT_OVERDUE", "PAYMENT_PARTIALLY_REFUNDED"} | PAID_EVENTS | REVERSAL_EVENTS
ENDED_SUBSCRIPTION_EVENTS = {"SUBSCRIPTION_INACTIVATED", "SUBSCRIPTION_DELETED"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cents(value) -> int | None:
    return None if value is None else int(round(float(value) * 100))


def _date(value) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value)[:10])


def _add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    for d in (day.day, 30, 29, 28):
        try:
            return date(year, month, d)
        except ValueError:
            continue
    raise ValueError(day)


def _rows(result):
    return (result.data if result is not None else None) or []


def _user_for_customer(env: str, customer_id: str | None) -> str | None:
    if not customer_id:
        return None
    rows = _rows(supabase.table("billing_customers").select("user_id")
                 .eq("environment", env).eq("asaas_customer_id", customer_id).limit(1).execute())
    return rows[0]["user_id"] if rows else None


def _subscription(env: str, asaas_id: str | None) -> dict | None:
    if not asaas_id:
        return None
    rows = _rows(supabase.table("billing_subscriptions").select("*")
                 .eq("environment", env).eq("asaas_subscription_id", asaas_id).limit(1).execute())
    return rows[0] if rows else None


def _latest_checkout(env: str, user_id: str) -> dict | None:
    rows = _rows(supabase.table("billing_checkouts").select("*").eq("environment", env)
                 .eq("user_id", user_id).in_("status", ["active", "paid"])
                 .order("created_at", desc=True).limit(1).execute())
    return rows[0] if rows else None


def _ensure_subscription(env: str, asaas_id: str, user_id: str, source: dict) -> dict | None:
    """Cria o registro local da assinatura a partir do último checkout da conta."""
    found = _subscription(env, asaas_id)
    if found:
        return found
    order = _latest_checkout(env, user_id)
    if not order:
        logger.warning("Assinatura %s sem checkout correspondente; ignorada", asaas_id)
        return None
    row = {
        "user_id": user_id, "environment": env, "asaas_subscription_id": asaas_id,
        "tier": order["tier"], "period": order["period"],
        "billing_type": source.get("billingType") if source.get("billingType") in ("CREDIT_CARD", "PIX")
        else order["billing_type"],
        "value_cents": _cents(source.get("value")) or order["value_cents"], "status": "pending",
    }
    supabase.table("billing_subscriptions").upsert(
        row, on_conflict="environment,asaas_subscription_id").execute()
    return _subscription(env, asaas_id)


def _other_open_subscription(sub: dict) -> bool:
    rows = _rows(supabase.table("billing_subscriptions").select("id").eq("environment", sub["environment"])
                 .eq("user_id", sub["user_id"]).in_("status", ["active", "overdue"]).neq("id", sub["id"])
                 .limit(1).execute())
    return bool(rows)


def _downgrade(sub: dict, reason: str) -> None:
    if _other_open_subscription(sub):
        return
    _set_plan(sub["user_id"], "free", reason)


def _set_plan(user_id: str, tier: str, reason: str) -> None:
    if not asaas_client.may_bill(user_id):
        logger.warning("Plano não alterado: conta fora da lista de testes do sandbox")
        return
    supabase.table("users").update({"plan_tier": tier}).eq("id", user_id).execute()
    logger.info("Plano da conta alterado para %s (%s)", tier, reason)


def _update_subscription(sub: dict, **fields) -> None:
    fields["updated_at"] = _now().isoformat()
    supabase.table("billing_subscriptions").update(fields).eq("id", sub["id"]).execute()
    sub.update(fields)


def _record_payment(env: str, payment: dict, user_id: str | None, status: str) -> None:
    supabase.table("billing_payments").upsert({
        "environment": env, "asaas_payment_id": payment["id"], "user_id": user_id,
        "asaas_subscription_id": payment.get("subscription"), "billing_type": payment.get("billingType"),
        "status": status, "value_cents": _cents(payment.get("value")),
        "due_date": payment.get("dueDate"), "invoice_url": payment.get("invoiceUrl"),
        "paid_at": payment.get("clientPaymentDate") or payment.get("paymentDate") or payment.get("confirmedDate"),
        "updated_at": _now().isoformat(),
    }, on_conflict="environment,asaas_payment_id").execute()


def _months(period: str) -> int:
    return billing_pricing.DEFAULT_PERIODS.get(period, (1, "", 0))[0]


def apply_event(env: str, event: str, payload: dict) -> None:
    if event == "CHECKOUT_PAID":
        checkout = payload.get("checkout") or {}
        if checkout.get("id"):
            supabase.table("billing_checkouts").update(
                {"status": "paid", "updated_at": _now().isoformat()}
            ).eq("environment", env).eq("asaas_checkout_id", checkout["id"]).execute()
        return
    if event in ("CHECKOUT_CANCELED", "CHECKOUT_EXPIRED"):
        checkout = payload.get("checkout") or {}
        if checkout.get("id"):
            status = "canceled" if event == "CHECKOUT_CANCELED" else "expired"
            supabase.table("billing_checkouts").update(
                {"status": status, "updated_at": _now().isoformat()}
            ).eq("environment", env).eq("asaas_checkout_id", checkout["id"]).neq("status", "paid").execute()
        return
    if event == "SUBSCRIPTION_CREATED":
        sub = payload.get("subscription") or {}
        user_id = _user_for_customer(env, sub.get("customer"))
        if sub.get("id") and user_id:
            _ensure_subscription(env, sub["id"], user_id, sub)
        return
    if event in ENDED_SUBSCRIPTION_EVENTS:
        found = _subscription(env, (payload.get("subscription") or {}).get("id"))
        if found and found["status"] != "canceled":
            # Plano segue até o fim do período pago; o job diário faz a volta a Free.
            _update_subscription(found, status="canceled")
        return
    if event not in PAYMENT_RECORD_EVENTS:
        return
    payment = payload.get("payment") or {}
    if not payment.get("id"):
        return
    user_id = _user_for_customer(env, payment.get("customer"))
    _record_payment(env, payment, user_id, payment.get("status") or event)
    if not user_id or not payment.get("subscription"):
        return
    sub = _ensure_subscription(env, payment["subscription"], user_id, payment)
    if not sub:
        return
    if event in PAID_EVENTS:
        due = _date(payment.get("dueDate")) or _now().date()
        end = _add_months(due, _months(sub["period"]))
        current = _date(sub.get("current_period_end"))
        _update_subscription(sub, status="active", overdue_since=None,
                             current_period_end=max(end, current).isoformat() if current else end.isoformat())
        _set_plan(user_id, sub["tier"], event)
    elif event == "PAYMENT_OVERDUE":
        if sub["status"] in ("active", "pending", "overdue"):
            since = sub.get("overdue_since") or (_date(payment.get("dueDate")) or _now().date()).isoformat()
            _update_subscription(sub, status="overdue", overdue_since=since)
    elif event in REVERSAL_EVENTS:
        _update_subscription(sub, status="canceled", current_period_end=_now().date().isoformat())
        _downgrade(sub, event)


def process_pending_events(limit: int = 50) -> int:
    """Aplica eventos pendentes do ambiente atual. Retorna quantos foram processados."""
    if not asaas_client.enabled():
        return 0
    env = asaas_client.environment()
    rows = _rows(supabase.table("billing_webhook_events").select("*").eq("environment", env)
                 .is_("processed_at", "null").lt("attempts", MAX_ATTEMPTS)
                 .order("received_at").limit(limit).execute())
    done = 0
    for row in rows:
        try:
            apply_event(env, row["event_type"], row.get("payload") or {})
            supabase.table("billing_webhook_events").update(
                {"processed_at": _now().isoformat(), "attempts": row.get("attempts", 0) + 1, "last_error": None}
            ).eq("environment", env).eq("event_id", row["event_id"]).execute()
            done += 1
        except Exception as exc:
            logger.exception("Falha ao aplicar evento de cobrança %s", row.get("event_type"))
            supabase.table("billing_webhook_events").update(
                {"attempts": row.get("attempts", 0) + 1, "last_error": type(exc).__name__}
            ).eq("environment", env).eq("event_id", row["event_id"]).execute()
            # Mantém a ordem: não aplica eventos mais novos antes deste.
            break
    return done


def expire_lapsed_subscriptions(today: date | None = None) -> int:
    """Volta a Free: atraso além da tolerância e assinaturas canceladas já vencidas."""
    if not asaas_client.enabled():
        return 0
    env = asaas_client.environment()
    today = today or _now().date()
    changed = 0
    overdue = _rows(supabase.table("billing_subscriptions").select("*").eq("environment", env)
                    .eq("status", "overdue").lte("overdue_since",
                                                 (today - timedelta(days=GRACE_DAYS)).isoformat()).execute())
    for sub in overdue:
        _update_subscription(sub, status="inactive")
        _downgrade(sub, "atraso acima de 15 dias")
        changed += 1
    ended = _rows(supabase.table("billing_subscriptions").select("*").eq("environment", env)
                  .eq("status", "canceled").lt("current_period_end", today.isoformat()).execute())
    for sub in ended:
        _update_subscription(sub, status="inactive")
        _downgrade(sub, "assinatura encerrada")
        changed += 1
    return changed


def run_billing_jobs() -> None:
    """Entrada do agendador: nunca propaga exceção."""
    try:
        process_pending_events()
        expire_lapsed_subscriptions()
    except Exception:
        logger.exception("Falha no job de cobrança")

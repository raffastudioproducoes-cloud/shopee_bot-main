"""Preços dos planos pagos por período (cobrança Asaas).

O valor cobrado é sempre calculado aqui, no servidor, a partir das tabelas
`plan_prices` e `plan_periods`; o navegador só exibe. Se o banco não
responder, usa os valores aprovados por Rafa em 10/11/2026.
"""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

logger = logging.getLogger(__name__)

PAID_TIERS = ("pro", "premium")
DEFAULT_MONTHLY_CENTS = {"pro": 5990, "premium": 10990}
# período -> (meses, ciclo do Asaas, desconto em pontos-base)
DEFAULT_PERIODS = {
    "monthly": (1, "MONTHLY", 0),
    "quarterly": (3, "QUARTERLY", 250),
    "semiannual": (6, "SEMIANNUALLY", 500),
    "yearly": (12, "YEARLY", 1500),
}
PERIOD_ORDER = tuple(DEFAULT_PERIODS)


def period_total_cents(monthly_cents: int, months: int, discount_bps: int) -> int:
    """Total do ciclo em centavos, arredondado meio para cima."""
    total = Decimal(monthly_cents) * months * (Decimal(10000 - discount_bps) / Decimal(10000))
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def per_month_cents(total_cents: int, months: int) -> int:
    return int((Decimal(total_cents) / months).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _load(supabase) -> tuple[dict[str, int], dict[str, tuple[int, str, int]]]:
    prices, periods = dict(DEFAULT_MONTHLY_CENTS), dict(DEFAULT_PERIODS)
    if supabase is None:
        return prices, periods
    try:
        rows = supabase.table("plan_prices").select("tier,monthly_price_cents").execute().data or []
        for r in rows:
            if r.get("tier") in PAID_TIERS and int(r.get("monthly_price_cents") or 0) > 0:
                prices[r["tier"]] = int(r["monthly_price_cents"])
        rows = (supabase.table("plan_periods").select("period,months,asaas_cycle,discount_bps")
                .execute().data or [])
        for r in rows:
            if r.get("period") in DEFAULT_PERIODS:
                periods[r["period"]] = (int(r["months"]), str(r["asaas_cycle"]), int(r["discount_bps"]))
    except Exception as exc:  # banco fora: segue com os valores aprovados
        logger.warning("Preços dos planos indisponíveis no banco: %s", type(exc).__name__)
    return prices, periods


def price_table(supabase=None) -> list[dict]:
    """Tabela completa para a tela de planos."""
    prices, periods = _load(supabase)
    out = []
    for tier in PAID_TIERS:
        for period in PERIOD_ORDER:
            months, cycle, bps = periods[period]
            total = period_total_cents(prices[tier], months, bps)
            out.append({
                "tier": tier, "period": period, "months": months, "cycle": cycle,
                "discount_bps": bps, "monthly_price_cents": prices[tier],
                "total_cents": total, "per_month_cents": per_month_cents(total, months),
                "savings_cents": prices[tier] * months - total,
            })
    return out


def quote(supabase, tier: str, period: str) -> dict:
    """Preço de uma combinação; ValueError se o plano/período não existir."""
    for row in price_table(supabase):
        if row["tier"] == tier and row["period"] == period:
            return row
    raise ValueError("plano ou período inválido")

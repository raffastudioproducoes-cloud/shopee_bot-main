"""Cobrança Asaas, fase 1: preços calculados no servidor e webhook idempotente."""
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from api import asaas_client, billing_pricing
from api import database as database_module
from api.config import settings
from api.main import app

TOKEN = "t" * 40


def _price(rows, tier, period):
    return next(r for r in rows if r["tier"] == tier and r["period"] == period)


def test_default_price_table_matches_approved_values():
    rows = billing_pricing.price_table(None)
    assert len(rows) == 8
    expected = {
        ("pro", "monthly"): (5990, 5990), ("pro", "quarterly"): (17521, 5840),
        ("pro", "semiannual"): (34143, 5691), ("pro", "yearly"): (61098, 5092),
        ("premium", "monthly"): (10990, 10990), ("premium", "quarterly"): (32146, 10715),
        ("premium", "semiannual"): (62643, 10441), ("premium", "yearly"): (112098, 9342),
    }
    for (tier, period), (total, per_month) in expected.items():
        row = _price(rows, tier, period)
        assert (row["total_cents"], row["per_month_cents"]) == (total, per_month)
    assert _price(rows, "pro", "yearly")["cycle"] == "YEARLY"
    assert _price(rows, "pro", "yearly")["savings_cents"] == 5990 * 12 - 61098


def test_prices_come_from_database_when_available():
    fake = MagicMock()
    tables = {
        "plan_prices": [{"tier": "pro", "monthly_price_cents": 10000}],
        "plan_periods": [{"period": "yearly", "months": 12, "asaas_cycle": "YEARLY", "discount_bps": 2000}],
    }
    fake.table.side_effect = lambda name: MagicMock(**{
        "select.return_value.execute.return_value": MagicMock(data=tables[name])})
    row = billing_pricing.quote(fake, "pro", "yearly")
    assert row["total_cents"] == 96000 and row["monthly_price_cents"] == 10000
    # Premium sem linha no banco mantém o valor aprovado.
    assert billing_pricing.quote(fake, "premium", "monthly")["total_cents"] == 10990


def test_database_failure_falls_back_to_approved_prices():
    fake = MagicMock()
    fake.table.side_effect = RuntimeError("down")
    assert billing_pricing.quote(fake, "premium", "yearly")["total_cents"] == 112098


def test_quote_rejects_unknown_plan_or_period():
    with pytest.raises(ValueError):
        billing_pricing.quote(None, "free", "monthly")
    with pytest.raises(ValueError):
        billing_pricing.quote(None, "pro", "ninemonths")


def test_plans_endpoint_is_public_and_server_computed(monkeypatch):
    monkeypatch.setattr(database_module, "get_supabase", lambda: None)
    app.dependency_overrides.clear()
    res = TestClient(app).get("/billing/plans")
    assert res.status_code == 200
    body = res.json()
    assert body["currency"] == "BRL"
    assert _price(body["prices"], "premium", "quarterly")["total_cents"] == 32146


@pytest.fixture
def webhook(monkeypatch):
    monkeypatch.setattr(settings, "asaas_webhook_token", TOKEN)
    fake = MagicMock()
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    app.dependency_overrides.clear()
    return TestClient(app), fake


EVENT = {"id": "evt_1", "event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}}


def test_webhook_disabled_without_token(monkeypatch):
    monkeypatch.setattr(settings, "asaas_webhook_token", "")
    res = TestClient(app).post("/billing/webhook/asaas", json=EVENT)
    assert res.status_code == 503


def test_webhook_rejects_wrong_token(webhook):
    client, fake = webhook
    res = client.post("/billing/webhook/asaas", json=EVENT, headers={"asaas-access-token": "x" * 40})
    assert res.status_code == 401
    fake.table.assert_not_called()


def test_webhook_rejects_event_without_id(webhook):
    client, fake = webhook
    res = client.post("/billing/webhook/asaas", json={"event": "PAYMENT_RECEIVED"},
                      headers={"asaas-access-token": TOKEN})
    assert res.status_code == 400
    res = client.post("/billing/webhook/asaas", json=[1, 2], headers={"asaas-access-token": TOKEN})
    assert res.status_code == 400
    fake.table.assert_not_called()


def test_webhook_persists_event_idempotently(webhook):
    client, fake = webhook
    res = client.post("/billing/webhook/asaas", json=EVENT, headers={"asaas-access-token": TOKEN})
    assert res.status_code == 200 and res.json() == {"received": True}
    fake.table.assert_called_with("billing_webhook_events")
    args, kwargs = fake.table.return_value.upsert.call_args
    assert args[0]["event_id"] == "evt_1" and args[0]["event_type"] == "PAYMENT_RECEIVED"
    assert args[0]["environment"] == "sandbox"
    assert kwargs == {"on_conflict": "environment,event_id", "ignore_duplicates": True}


def test_webhook_storage_failure_is_not_acknowledged(webhook):
    client, fake = webhook
    fake.table.return_value.upsert.return_value.execute.side_effect = RuntimeError("db")
    res = client.post("/billing/webhook/asaas", json=EVENT, headers={"asaas-access-token": TOKEN})
    assert res.status_code == 503


def _transport(status, body, seen):
    def handler(request):
        seen.append(request)
        return httpx.Response(status, json=body)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_client_sends_key_only_in_header_and_maps_errors(monkeypatch):
    monkeypatch.setattr(settings, "asaas_api_key", "$aact_secret_key")
    seen = []
    out = asaas_client.request("POST", "/customers", json={"name": "A"},
                               client=_transport(200, {"id": "cus_1"}, seen))
    assert out == {"id": "cus_1"}
    req = seen[0]
    assert req.headers["access_token"] == "$aact_secret_key"
    assert req.headers["user-agent"] == settings.asaas_user_agent
    assert str(req.url) == "https://api-sandbox.asaas.com/v3/customers"
    with pytest.raises(asaas_client.AsaasError) as err:
        asaas_client.request("POST", "/customers", client=_transport(
            400, {"errors": [{"code": "invalid_cpfCnpj", "description": "CPF inválido"}]}, []))
    assert err.value.messages == ["CPF inválido"] and "secret" not in str(err.value)
    with pytest.raises(asaas_client.AsaasUnavailable):
        asaas_client.request("GET", "/customers", client=_transport(502, {}, []))


def test_client_refuses_without_key(monkeypatch):
    monkeypatch.setattr(settings, "asaas_api_key", "")
    with pytest.raises(asaas_client.AsaasUnavailable):
        asaas_client.request("GET", "/customers")


def test_environment_follows_url(monkeypatch):
    monkeypatch.setattr(settings, "asaas_api_url", "https://api.asaas.com/v3")
    assert asaas_client.environment() == "production"
    assert asaas_client.checkout_url("abc") == "https://asaas.com/checkoutSession/show?id=abc"


def test_migration_keeps_billing_tables_out_of_the_browser():
    sql = open("database/migrations/098_billing_asaas.sql").read()
    for table in ("plan_prices", "plan_periods", "billing_customers", "billing_checkouts",
                  "billing_subscriptions", "billing_payments", "billing_webhook_events"):
        assert f"public.{table}" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql and "FROM PUBLIC, anon, authenticated" in sql
    assert "('pro', 5990), ('premium', 10990)" in sql
    assert "('yearly', 12, 'YEARLY', 1500)" in sql
    assert "DROP TABLE" not in sql.upper() and "DELETE FROM" not in sql.upper()

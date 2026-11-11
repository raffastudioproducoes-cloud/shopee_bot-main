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


# ---------- fase 2: criação do checkout ----------
from api.crypto import encrypt  # noqa: E402
from api.routers import billing as billing_router  # noqa: E402
from api.routers.auth import get_current_user_id  # noqa: E402


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.filters = db, name, "select", None, {}

    def select(self, *_a, **_k):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload; return self

    def update(self, payload):
        self.op, self.payload = "update", payload; return self

    def upsert(self, payload, **_k):
        self.op, self.payload = "upsert", payload; return self

    def eq(self, col, val):
        self.filters[col] = val; return self

    def in_(self, col, vals):
        self.filters[col] = tuple(vals); return self

    def gte(self, *_a):
        return self

    def limit(self, *_a):
        return self

    def maybe_single(self):
        self.single = True; return self

    def execute(self):
        self.db.calls.append((self.name, self.op, self.payload, dict(self.filters)))
        if self.op == "insert":
            return MagicMock(data=[{"id": "order-1", **self.payload}])
        if self.op != "select":
            return MagicMock(data=[self.payload])
        rows = self.db.rows.get(self.name)
        if getattr(self, "single", False):
            return MagicMock(data=rows[0] if rows else None)
        return MagicMock(data=rows or [])


class _DB:
    def __init__(self, **rows):
        self.rows, self.calls = rows, []

    def table(self, name):
        return _Q(self, name)


IDENTITY = {"full_name": "Maria Teste", "cpf_ciphertext": encrypt("52998224725"),
            "mobile_phone": "+5511987654321"}


@pytest.fixture
def checkout(monkeypatch):
    monkeypatch.setattr(settings, "asaas_api_key", "$aact_test")
    monkeypatch.setattr(settings, "asaas_api_url", "https://api-sandbox.asaas.com/v3")
    monkeypatch.setattr(settings, "asaas_sandbox_testers", "u1")
    db = _DB(users=[{"id": "u1", "email": "m@example.com"}], account_billing_identity=[IDENTITY])
    monkeypatch.setattr(database_module, "get_supabase", lambda: db)
    sent = []
    monkeypatch.setattr(asaas_client, "create_customer", lambda **kw: sent.append(("customer", kw)) or {"id": "cus_1"})
    monkeypatch.setattr(asaas_client, "create_checkout", lambda body: sent.append(("checkout", body)) or {"id": "chk_1"})
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "u1"
    yield TestClient(app), db, sent
    app.dependency_overrides.clear()


BODY = {"tier": "pro", "period": "yearly", "billing_type": "CREDIT_CARD"}


def test_checkout_creates_customer_and_recurrent_checkout(checkout):
    client, db, sent = checkout
    res = client.post("/billing/checkout", json=BODY)
    assert res.status_code == 200, res.text
    assert res.json()["checkout_url"].endswith("checkoutSession/show?id=chk_1")
    assert res.json()["value_cents"] == 61098
    customer = sent[0][1]
    assert customer["cpf_cnpj"] == "52998224725" and customer["mobile_phone"] == "11987654321"
    body = sent[1][1]
    assert body["customer"] == "cus_1" and body["chargeTypes"] == ["RECURRENT"]
    assert body["billingTypes"] == ["CREDIT_CARD"] and body["externalReference"] == "order-1"
    assert body["subscription"]["cycle"] == "YEARLY"
    assert body["items"][0]["value"] == 610.98
    # Plano nunca é alterado aqui.
    assert not any(name == "users" and op != "select" for name, op, *_ in db.calls)
    assert ("billing_checkouts", "update", {"asaas_checkout_id": "chk_1", "status": "active"},
            {"id": "order-1"}) in db.calls


def test_checkout_requires_complete_identity(checkout):
    client, db, sent = checkout
    db.rows["account_billing_identity"] = [{"full_name": "Maria Teste"}]
    res = client.post("/billing/checkout", json=BODY)
    assert res.status_code == 422
    assert "CPF" in res.json()["detail"]["missing"] and not sent


def test_checkout_blocks_second_subscription(checkout):
    client, db, sent = checkout
    db.rows["billing_subscriptions"] = [{"id": "s1"}]
    assert client.post("/billing/checkout", json=BODY).status_code == 409 and not sent


def test_checkout_rejects_unknown_period_and_free(checkout):
    client, _db, sent = checkout
    assert client.post("/billing/checkout", json={**BODY, "period": "ninemonths"}).status_code == 422
    assert client.post("/billing/checkout", json={**BODY, "tier": "free"}).status_code == 422
    assert not sent


def test_checkout_reuses_existing_customer(checkout):
    client, db, sent = checkout
    db.rows["billing_customers"] = [{"asaas_customer_id": "cus_old"}]
    assert client.post("/billing/checkout", json={**BODY, "billing_type": "PIX"}).status_code == 200
    assert [k for k, _ in sent] == ["checkout"] and sent[0][1]["customer"] == "cus_old"
    assert sent[0][1]["billingTypes"] == ["PIX"]


def test_checkout_disabled_without_key(checkout, monkeypatch):
    client, _db, sent = checkout
    monkeypatch.setattr(settings, "asaas_api_key", "")
    assert client.post("/billing/checkout", json=BODY).status_code == 503 and not sent


def test_checkout_asaas_refusal_marks_order_failed(checkout, monkeypatch):
    client, db, _sent = checkout

    def refuse(body):
        raise asaas_client.AsaasError(400, ["Cliente inválido"])
    monkeypatch.setattr(asaas_client, "create_checkout", refuse)
    res = client.post("/billing/checkout", json=BODY)
    assert res.status_code == 422 and res.json()["detail"]["details"] == ["Cliente inválido"]
    assert ("billing_checkouts", "update", {"status": "failed"}, {"id": "order-1"}) in db.calls


def test_checkout_requires_login():
    app.dependency_overrides.clear()
    assert TestClient(app).post("/billing/checkout", json=BODY).status_code == 401


def test_checkout_rate_limited(checkout):
    client, db, sent = checkout
    db.rows["billing_checkouts"] = [{"id": i} for i in range(billing_router.MAX_CHECKOUTS_PER_HOUR)]
    assert client.post("/billing/checkout", json=BODY).status_code == 429 and not sent


def test_sandbox_checkout_only_for_listed_testers(checkout, monkeypatch):
    client, _db, sent = checkout
    monkeypatch.setattr(settings, "asaas_sandbox_testers", "outra-conta")
    assert client.post("/billing/checkout", json=BODY).status_code == 403 and not sent
    monkeypatch.setattr(settings, "asaas_api_url", "https://api.asaas.com/v3")
    assert client.post("/billing/checkout", json=BODY).status_code == 200


# ---------- ADMIN: status e registro do webhook ----------
@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setattr(settings, "asaas_api_key", "$aact_test")
    monkeypatch.setattr(settings, "asaas_webhook_token", TOKEN)
    monkeypatch.setattr(settings, "frontend_url", "https://staging.example.com")
    db = _DB(users=[{"id": "a1", "access": "ADMIN", "email": "admin@example.com"}])
    monkeypatch.setattr(database_module, "get_supabase", lambda: db)
    calls = []

    def fake_request(method, path, **kw):
        calls.append((method, path, kw))
        if method == "GET":
            return {"data": calls_existing}
        return {"id": "wh_1"}
    calls_existing = []
    monkeypatch.setattr(asaas_client, "request", fake_request)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "a1"
    yield TestClient(app), db, calls, calls_existing
    app.dependency_overrides.clear()


def test_admin_status_never_reveals_secrets(admin):
    client, _db, _calls, _ex = admin
    body = client.get("/admin/billing/status").json()
    assert body["api_key_configured"] and body["webhook_token_configured"]
    assert body["webhook_url"] == "https://staging.example.com/api/billing/webhook/asaas"
    assert TOKEN not in str(body) and "aact" not in str(body)


def test_admin_registers_webhook_with_server_token(admin):
    client, _db, calls, _ex = admin
    res = client.post("/admin/billing/webhook", json={})
    assert res.status_code == 200 and res.json()["updated"] is False
    method, path, kw = calls[-1]
    assert (method, path) == ("POST", "/webhooks")
    assert kw["json"]["authToken"] == TOKEN and kw["json"]["sendType"] == "SEQUENTIALLY"
    assert "PAYMENT_CONFIRMED" in kw["json"]["events"] and kw["json"]["email"] == "admin@example.com"
    assert TOKEN not in res.text


def test_admin_updates_existing_webhook(admin):
    client, _db, calls, existing = admin
    existing.append({"id": "wh_9", "url": "https://staging.example.com/api/billing/webhook/asaas"})
    assert client.post("/admin/billing/webhook", json={}).json()["updated"] is True
    assert calls[-1][:2] == ("PUT", "/webhooks/wh_9")


def test_billing_admin_routes_require_admin(admin):
    client, db, calls, _ex = admin
    db.rows["users"] = [{"id": "a1", "access": "USER"}]
    assert client.get("/admin/billing/status").status_code == 403
    assert client.post("/admin/billing/webhook", json={}).status_code == 403
    assert not calls

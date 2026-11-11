"""Cobrança Asaas, fase 3: eventos ativam, mantêm e baixam o plano corretamente."""
from datetime import date

import pytest

from api import billing_events
from api import database as database_module
from api.config import settings


class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.preds, self.on_conflict = db, name, "select", None, [], None
        self._order, self._limit = None, None

    def select(self, *_):
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload; return self

    def upsert(self, payload, on_conflict=None, **_):
        self.op, self.payload, self.on_conflict = "upsert", payload, on_conflict; return self

    def eq(self, c, v):
        self.preds.append(lambda r: r.get(c) == v); return self

    def neq(self, c, v):
        self.preds.append(lambda r: r.get(c) != v); return self

    def in_(self, c, vs):
        self.preds.append(lambda r: r.get(c) in vs); return self

    def is_(self, c, _v):
        self.preds.append(lambda r: r.get(c) is None); return self

    def lt(self, c, v):
        self.preds.append(lambda r: r.get(c) is not None and r.get(c) < v); return self

    def lte(self, c, v):
        self.preds.append(lambda r: r.get(c) is not None and r.get(c) <= v); return self

    def order(self, c, desc=False):
        self._order = (c, desc); return self

    def limit(self, n):
        self._limit = n; return self

    def execute(self):
        rows = self.db.t.setdefault(self.name, [])
        match = [r for r in rows if all(p(r) for p in self.preds)]
        if self.op == "select":
            if self._order:
                match.sort(key=lambda r: r.get(self._order[0]) or "", reverse=self._order[1])
            return _Res([dict(r) for r in match[: self._limit or None]])
        if self.op == "update":
            for r in match:
                r.update(self.payload)
            return _Res(match)
        keys = self.on_conflict.split(",")
        for r in rows:
            if all(r.get(k) == self.payload.get(k) for k in keys):
                r.update(self.payload); return _Res([r])
        row = {"id": f"{self.name}-{len(rows) + 1}", **self.payload}
        rows.append(row)
        return _Res([row])


class _DB:
    def __init__(self):
        self.t = {
            "users": [{"id": "u1", "plan_tier": "free"}],
            "billing_customers": [{"user_id": "u1", "environment": "sandbox", "asaas_customer_id": "cus_1"}],
            "billing_checkouts": [{"id": "o1", "user_id": "u1", "environment": "sandbox", "tier": "premium",
                                   "period": "quarterly", "billing_type": "CREDIT_CARD", "value_cents": 32146,
                                   "status": "active", "asaas_checkout_id": "chk_1", "created_at": "2026-11-11"}],
        }

    def table(self, name):
        return _Q(self, name)

    def plan(self):
        return self.t["users"][0]["plan_tier"]

    def sub(self):
        return self.t["billing_subscriptions"][0]


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(settings, "asaas_api_key", "$aact_test")
    monkeypatch.setattr(settings, "asaas_api_url", "https://api-sandbox.asaas.com/v3")
    monkeypatch.setattr(settings, "asaas_sandbox_testers", "u1")
    fake = _DB()
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    return fake


def _pay(event, pid="pay_1", due="2026-11-11", status=None):
    return {"payment": {"id": pid, "customer": "cus_1", "subscription": "sub_1", "value": 321.46,
                        "billingType": "CREDIT_CARD", "dueDate": due, "status": status or event}}


def _apply(event, payload):
    billing_events.apply_event("sandbox", event, payload)


def test_paid_activates_plan_until_end_of_period(db):
    _apply("CHECKOUT_PAID", {"checkout": {"id": "chk_1"}})
    assert db.t["billing_checkouts"][0]["status"] == "paid"
    _apply("SUBSCRIPTION_CREATED", {"subscription": {"id": "sub_1", "customer": "cus_1", "value": 321.46}})
    assert db.sub()["tier"] == "premium" and db.sub()["status"] == "pending" and db.plan() == "free"
    _apply("PAYMENT_CONFIRMED", _pay("PAYMENT_CONFIRMED"))
    assert db.plan() == "premium"
    assert db.sub()["status"] == "active" and db.sub()["current_period_end"] == "2027-02-11"
    assert db.t["billing_payments"][0]["value_cents"] == 32146


def test_payment_before_subscription_event_still_activates(db):
    _apply("PAYMENT_RECEIVED", _pay("PAYMENT_RECEIVED"))
    assert db.plan() == "premium" and db.sub()["asaas_subscription_id"] == "sub_1"


def test_overdue_keeps_plan_within_grace_then_downgrades(db):
    _apply("PAYMENT_CONFIRMED", _pay("PAYMENT_CONFIRMED"))
    _apply("PAYMENT_OVERDUE", _pay("PAYMENT_OVERDUE", pid="pay_2", due="2027-02-11"))
    assert db.sub()["status"] == "overdue" and db.sub()["overdue_since"] == "2027-02-11"
    assert billing_events.expire_lapsed_subscriptions(date(2027, 2, 25)) == 0
    assert db.plan() == "premium"
    assert billing_events.expire_lapsed_subscriptions(date(2027, 2, 26)) == 1
    assert db.plan() == "free" and db.sub()["status"] == "inactive"


def test_late_payment_within_grace_restores_active(db):
    _apply("PAYMENT_CONFIRMED", _pay("PAYMENT_CONFIRMED"))
    _apply("PAYMENT_OVERDUE", _pay("PAYMENT_OVERDUE", pid="pay_2", due="2027-02-11"))
    _apply("PAYMENT_RECEIVED", _pay("PAYMENT_RECEIVED", pid="pay_2", due="2027-02-11"))
    assert db.sub()["status"] == "active" and db.sub()["overdue_since"] is None
    assert db.sub()["current_period_end"] == "2027-05-11" and db.plan() == "premium"


def test_refund_or_chargeback_downgrades_now(db):
    _apply("PAYMENT_CONFIRMED", _pay("PAYMENT_CONFIRMED"))
    _apply("PAYMENT_CHARGEBACK_REQUESTED", _pay("PAYMENT_CHARGEBACK_REQUESTED"))
    assert db.plan() == "free" and db.sub()["status"] == "canceled"


def test_cancel_keeps_plan_until_paid_period_ends(db):
    _apply("PAYMENT_CONFIRMED", _pay("PAYMENT_CONFIRMED"))
    _apply("SUBSCRIPTION_DELETED", {"subscription": {"id": "sub_1"}})
    assert db.sub()["status"] == "canceled" and db.plan() == "premium"
    assert billing_events.expire_lapsed_subscriptions(date(2027, 2, 11)) == 0
    assert billing_events.expire_lapsed_subscriptions(date(2027, 2, 12)) == 1
    assert db.plan() == "free"


def test_sandbox_never_changes_plan_of_non_tester(db, monkeypatch):
    monkeypatch.setattr(settings, "asaas_sandbox_testers", "outra-conta")
    _apply("PAYMENT_CONFIRMED", _pay("PAYMENT_CONFIRMED"))
    assert db.plan() == "free"


def test_unknown_customer_is_ignored(db):
    payload = _pay("PAYMENT_CONFIRMED")
    payload["payment"]["customer"] = "cus_x"
    _apply("PAYMENT_CONFIRMED", payload)
    assert db.plan() == "free" and "billing_subscriptions" not in db.t


def test_pending_events_processed_in_order_and_marked(db):
    db.t["billing_webhook_events"] = [
        {"environment": "sandbox", "event_id": "e2", "event_type": "PAYMENT_CONFIRMED",
         "payload": _pay("PAYMENT_CONFIRMED"), "received_at": "2026-11-11T10:00:02", "processed_at": None,
         "attempts": 0},
        {"environment": "sandbox", "event_id": "e1", "event_type": "CHECKOUT_PAID",
         "payload": {"checkout": {"id": "chk_1"}}, "received_at": "2026-11-11T10:00:01", "processed_at": None,
         "attempts": 0},
        {"environment": "production", "event_id": "p1", "event_type": "PAYMENT_CONFIRMED",
         "payload": _pay("PAYMENT_CONFIRMED"), "received_at": "2026-11-11T10:00:00", "processed_at": None,
         "attempts": 0},
    ]
    assert billing_events.process_pending_events() == 2
    events = {e["event_id"]: e for e in db.t["billing_webhook_events"]}
    assert events["e1"]["processed_at"] and events["e2"]["processed_at"]
    assert events["p1"]["processed_at"] is None  # outro ambiente não é tocado
    assert db.plan() == "premium"
    assert billing_events.process_pending_events() == 0


def test_failing_event_stops_queue_and_counts_attempt(db, monkeypatch):
    db.t["billing_webhook_events"] = [
        {"environment": "sandbox", "event_id": "e1", "event_type": "PAYMENT_CONFIRMED",
         "payload": _pay("PAYMENT_CONFIRMED"), "received_at": "1", "processed_at": None, "attempts": 0},
        {"environment": "sandbox", "event_id": "e2", "event_type": "CHECKOUT_PAID",
         "payload": {"checkout": {"id": "chk_1"}}, "received_at": "2", "processed_at": None, "attempts": 0},
    ]

    def boom(*_a):
        raise RuntimeError("db down")
    monkeypatch.setattr(billing_events, "apply_event", boom)
    assert billing_events.process_pending_events() == 0
    e1, e2 = db.t["billing_webhook_events"]
    assert e1["attempts"] == 1 and e1["last_error"] == "RuntimeError" and e2["attempts"] == 0


def test_jobs_do_nothing_without_key(db, monkeypatch):
    monkeypatch.setattr(settings, "asaas_api_key", "")
    assert billing_events.process_pending_events() == 0
    assert billing_events.expire_lapsed_subscriptions() == 0


def test_add_months_handles_month_end():
    assert billing_events._add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert billing_events._add_months(date(2026, 11, 11), 12) == date(2027, 11, 11)

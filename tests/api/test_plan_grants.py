"""Concessão de plano pelo ADMIN: autorização, validação de duração, expiração e auditoria."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api import database, plan_grants
from api.main import app
from api.routers import admin
from api.routers.auth import get_current_user_id

ADMIN = "00000000-0000-0000-0000-0000000000aa"
USER = "00000000-0000-0000-0000-0000000000b1"
OTHER_ADMIN = "00000000-0000-0000-0000-0000000000ab"
PLAIN = "00000000-0000-0000-0000-0000000000c1"


class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.preds, self._limit = db, name, "select", None, [], None
        self._single = False

    def select(self, *_):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def eq(self, c, v):
        self.preds.append(lambda r: r.get(c) == v)
        return self

    def in_(self, c, vs):
        self.preds.append(lambda r: r.get(c) in vs)
        return self

    def lte(self, c, v):
        self.preds.append(lambda r: r.get(c) is not None and r.get(c) <= v)
        return self

    def maybe_single(self):
        self._single = True
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = self.db.t.setdefault(self.name, [])
        if self.op == "insert":
            row = {"id": len(rows) + 1, **({"status": "active"} if self.name == "plan_grants" else {}), **self.payload}
            rows.append(row)
            return _Res([dict(row)])
        match = [r for r in rows if all(p(r) for p in self.preds)]
        if self.op == "update":
            for r in match:
                r.update(self.payload)
            return _Res([dict(r) for r in match])
        if self._single:
            return _Res(dict(match[0]) if match else None)
        return _Res([dict(r) for r in match[: self._limit or None]])


class _DB:
    def __init__(self):
        self.t = {
            "users": [
                {"id": ADMIN, "access": "ADMIN", "plan_tier": "free", "campaign_paid_through": None},
                {"id": OTHER_ADMIN, "access": "ADMIN", "plan_tier": "free", "campaign_paid_through": None},
                {"id": PLAIN, "access": "USER", "plan_tier": "free", "campaign_paid_through": None},
                {"id": USER, "username": "maria", "access": "USER", "plan_tier": "free",
                 "campaign_paid_through": None, "created_at": "2026-11-01T00:00:00+00:00", "updated_at": None},
            ],
        }

    def table(self, name):
        return _Q(self, name)

    def user(self):
        return next(r for r in self.t["users"] if r["id"] == USER)

    def grants(self):
        return self.t.get("plan_grants", [])


@pytest.fixture
def db(monkeypatch):
    fake = _DB()
    monkeypatch.setattr(database, "get_supabase", lambda: fake)
    admin._plan_attempts.clear()
    yield fake
    app.dependency_overrides.clear()


def _call(db, who, user_id, body):
    app.dependency_overrides[get_current_user_id] = lambda: who
    return TestClient(app).put(f"/admin/users/{user_id}/plan", json=body)


def test_non_admin_cannot_grant(db):
    response = _call(db, PLAIN, USER, {"plan": "premium", "days": 30})
    assert response.status_code == 403
    assert db.user()["plan_tier"] == "free" and db.grants() == []


def test_admin_grants_plan_with_audit_trail(db):
    response = _call(db, ADMIN, USER, {"plan": "premium", "days": 30, "reason": "teste interno"})
    assert response.status_code == 200
    body = response.json()
    expires = datetime.fromisoformat(body["plan_expires_at"])
    assert body["plan_tier"] == "premium"
    assert timedelta(days=29, hours=23) < expires - datetime.now(timezone.utc) <= timedelta(days=30)
    assert db.user()["plan_tier"] == "premium" and db.user()["campaign_paid_through"] == body["plan_expires_at"]
    grant = db.grants()[0]
    assert grant["granted_by"] == ADMIN and grant["user_id"] == USER and grant["tier"] == "premium"
    assert grant["expires_at"] == body["plan_expires_at"] and grant["status"] == "active"
    assert grant["previous_tier"] == "free" and grant["reason"] == "teste interno"
    assert db.t["audit_events"][0]["action"] == "plan_grant"


def test_grant_by_end_date(db):
    ends = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    response = _call(db, ADMIN, USER, {"plan": "pro", "ends_at": ends})
    assert response.status_code == 200 and db.user()["plan_tier"] == "pro"


@pytest.mark.parametrize("body", [
    {"plan": "pro", "days": 0},
    {"plan": "pro", "days": 366},
    {"plan": "pro"},
    {"plan": "pro", "days": 5, "ends_at": "2030-01-01T00:00:00+00:00"},
    {"plan": "gold", "days": 5},
    {"plan": "plus", "days": 5},
    {"plan": "free", "days": 5},
])
def test_invalid_requests_are_rejected_without_changes(db, body):
    assert _call(db, ADMIN, USER, body).status_code == 422
    assert db.user()["plan_tier"] == "free" and db.grants() == []


@pytest.mark.parametrize("delta", [timedelta(days=-1), timedelta(days=366)])
def test_end_date_outside_range_is_rejected(db, delta):
    ends = (datetime.now(timezone.utc) + delta).isoformat()
    response = _call(db, ADMIN, USER, {"plan": "pro", "ends_at": ends})
    assert response.status_code == 422
    assert db.user()["plan_tier"] == "free" and db.grants() == []


def test_unknown_user_and_invalid_id_are_404(db):
    assert _call(db, ADMIN, "00000000-0000-0000-0000-0000000000ff", {"plan": "pro", "days": 5}).status_code == 404
    assert _call(db, ADMIN, "not-a-uuid", {"plan": "pro", "days": 5}).status_code == 404


def test_admin_account_has_no_plan(db):
    assert _call(db, ADMIN, OTHER_ADMIN, {"plan": "pro", "days": 5}).status_code == 400


def test_open_subscription_blocks_manual_change(db):
    db.t["billing_subscriptions"] = [{"id": "s1", "user_id": USER, "status": "active"}]
    assert _call(db, ADMIN, USER, {"plan": "pro", "days": 5}).status_code == 409
    assert db.user()["plan_tier"] == "free" and db.grants() == []


def test_new_grant_supersedes_previous_and_free_revokes(db):
    _call(db, ADMIN, USER, {"plan": "pro", "days": 5})
    _call(db, ADMIN, USER, {"plan": "premium", "days": 10})
    assert [g["status"] for g in db.grants()] == ["superseded", "active"]
    response = _call(db, ADMIN, USER, {"plan": "free"})
    assert response.status_code == 200 and response.json()["plan_expires_at"] is None
    assert db.user()["plan_tier"] == "free" and db.user()["campaign_paid_through"] is None
    assert [g["status"] for g in db.grants()] == ["superseded", "revoked"]
    assert db.grants()[1]["ended_by"] == ADMIN
    assert db.t["audit_events"][-1]["action"] == "plan_remove"


def test_rate_limit_per_admin(db, monkeypatch):
    monkeypatch.setattr(admin, "_PLAN_RATE_ATTEMPTS", 1)
    assert _call(db, ADMIN, USER, {"plan": "pro", "days": 5}).status_code == 200
    assert _call(db, ADMIN, USER, {"plan": "pro", "days": 6}).status_code == 429


def test_expired_grant_returns_user_to_free(db):
    _call(db, ADMIN, USER, {"plan": "premium", "days": 5})
    later = datetime.now(timezone.utc) + timedelta(days=6)
    assert plan_grants.expire_due_grants(later) == 1
    assert db.user()["plan_tier"] == "free" and db.user()["campaign_paid_through"] is None
    assert db.grants()[0]["status"] == "expired" and db.grants()[0]["ended_at"]
    assert plan_grants.expire_due_grants(later) == 0


def test_unexpired_grant_is_kept(db):
    _call(db, ADMIN, USER, {"plan": "premium", "days": 5})
    assert plan_grants.expire_due_grants(datetime.now(timezone.utc) + timedelta(days=1)) == 0
    assert db.user()["plan_tier"] == "premium" and db.grants()[0]["status"] == "active"


def test_expiry_does_not_touch_a_plan_that_changed(db):
    _call(db, ADMIN, USER, {"plan": "premium", "days": 5})
    db.user()["plan_tier"] = "pro"
    plan_grants.expire_due_grants(datetime.now(timezone.utc) + timedelta(days=6))
    assert db.user()["plan_tier"] == "pro" and db.grants()[0]["status"] == "expired"


def test_user_list_exposes_plan_and_expiry(db):
    _call(db, ADMIN, USER, {"plan": "pro", "days": 7})
    app.dependency_overrides[get_current_user_id] = lambda: ADMIN
    rows = TestClient(app).get("/admin/users").json()["data"]
    maria = next(r for r in rows if r["id"] == USER)
    assert maria["plan_tier"] == "pro" and maria["plan_expires_at"] == db.user()["campaign_paid_through"]
    assert "campaign_paid_through" not in maria
    assert next(r for r in rows if r["id"] == ADMIN)["plan_expires_at"] is None

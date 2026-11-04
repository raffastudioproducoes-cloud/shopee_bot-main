"""F4D: contagens exatas/read-only e política por conta, sem DDL ou jobs."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import account_usage, campaign_policy
from api.main import app
from api.routers import profiles
from conftest import FakeDB


def database(tier="pro", access="USER"):
    return FakeDB({
        "users": [dict(id="owner", access=access, plan_tier=tier)],
        "campaign_reservations_f4e": [],
        "profiles": [dict(id="a", user_id="owner"), dict(id="b", user_id="owner"),
                     dict(id="foreign", user_id="other")],
        "plan_limits": [dict(tier="pro", products_per_account=500, lists_per_profile=20,
            immediate_per_hour=3, recurring_slots_per_day=5, max_profiles_per_account=3,
            active_campaigns_per_profile=2, campaign_days=15,
            campaign_posts_per_day=3, automation_enabled=False)],
        "products": [dict(id=1, user_id="owner", profile_id="a"),
                     dict(id=2, user_id="owner", profile_id="b"),
                     dict(id=3, user_id="other", profile_id="foreign")],
        "product_lists": [dict(id=1, user_id="owner", profile_id="a"),
                          dict(id=2, user_id="owner", profile_id="b"),
                          dict(id=3, user_id="owner", profile_id="b"),
                          dict(id=4, user_id="other", profile_id="a")],
    })


def bind(monkeypatch, db):
    monkeypatch.setattr(account_usage, "supabase", db)
    monkeypatch.setattr(campaign_policy, "supabase", db)


@pytest.mark.parametrize("tier", ["pro", "plus"])
def test_usage_is_scoped_exact_read_only_and_not_active_campaigns(monkeypatch, tier):
    db = database(tier)
    bind(monkeypatch, db)
    before = deepcopy(db.tables)
    result = account_usage.account_usage_response("owner", "a")
    assert result["plan_tier"] == "pro"
    assert result["resources"]["products"]["used"] == 2
    assert result["resources"]["products"]["limit"] == 500
    assert result["resources"]["lists"]["used"] == 1
    assert result["resources"]["profiles"]["used"] == 2
    assert account_usage.account_usage_response("owner", "b")["resources"]["lists"]["used"] == 2
    for resource in ("immediate", "recurring"):
        assert result["resources"][resource]["used"] is None
        assert result["resources"][resource]["usage_status"] == "unavailable"
    assert result["active_campaigns_count"] == 0
    assert result["activation_available"] is False
    assert result["automation_available"] is False
    assert db.tables == before


def test_admin_bypasses_only_commercial_limits_and_cannot_read_foreign_profile(monkeypatch):
    db = database("free", "ADMIN")
    bind(monkeypatch, db)
    result = account_usage.account_usage_response("owner", "a")
    assert result["is_admin"] is True
    assert all(row["limit"] is None and row["unlimited"] for row in result["resources"].values())
    with pytest.raises(HTTPException) as error:
        account_usage.account_usage_response("owner", "foreign")
    assert error.value.status_code == 404


def test_missing_policy_fails_closed_without_claiming_free(monkeypatch):
    db = database()
    db.tables["plan_limits"][0].pop("products_per_account")
    bind(monkeypatch, db)
    with pytest.raises(HTTPException) as error:
        account_usage.account_usage_response("owner", "a")
    assert error.value.status_code == 503


def test_count_none_and_failure_never_become_zero(monkeypatch):
    class Query:
        def select(self, *args, **kwargs):
            assert kwargs == {"count": "exact", "head": True}
            return self
        def eq(self, *args):
            return self
        def execute(self):
            return SimpleNamespace(count=None)
    monkeypatch.setattr(account_usage, "supabase", SimpleNamespace(table=lambda name: Query()))
    assert account_usage._count("products", "owner") is None
    monkeypatch.setattr(account_usage, "supabase", SimpleNamespace(table=lambda name: 1 / 0))
    assert account_usage._count("products", "owner") is None


def test_zero_is_only_displayed_after_successful_count(monkeypatch):
    db = database()
    db.tables["products"] = []
    bind(monkeypatch, db)
    row = account_usage.account_usage_response("owner", "a")["resources"]["products"]
    assert row["used"] == 0 and row["usage_status"] == "available"


def test_endpoint_requires_authentication_and_profile():
    assert TestClient(app).get("/profiles/usage").status_code == 401
    with pytest.raises(HTTPException) as error:
        asyncio.run(profiles.get_plan_usage(user_id="owner", profile_id=None))
    assert error.value.status_code == 400


def test_policy_reloaded_on_downgrade(monkeypatch):
    db = database()
    bind(monkeypatch, db)
    assert account_usage.account_usage_response("owner", "a")["campaigns_enabled"] is True
    db.tables["users"][0]["plan_tier"] = "free"
    db.tables["plan_limits"].append(dict(db.tables["plan_limits"][0], tier="free",
        active_campaigns_per_profile=0, campaign_days=0, campaign_posts_per_day=0,
        max_profiles_per_account=1, products_per_account=100))
    assert account_usage.account_usage_response("owner", "a")["campaigns_enabled"] is False

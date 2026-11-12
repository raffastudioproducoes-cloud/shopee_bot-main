"""ADMIN é sempre Premium (função central effective_plan); usuário comum segue o plano gravado."""
import asyncio

import pytest

from api import campaign_policy
from api.effective_plan import effective_plan
from api.routers import campaigns
from test_campaign_policy import database, setup_db


@pytest.mark.parametrize("access,stored,expected", [
    ("ADMIN", "free", "premium"),
    ("ADMIN", "pro", "premium"),
    ("ADMIN", "premium", "premium"),
    ("ADMIN", None, "premium"),
    ("USER", "free", "free"),
    ("USER", "pro", "pro"),
    ("USER", "plus", "pro"),
    ("USER", "premium", "premium"),
])
def test_effective_plan(access, stored, expected):
    assert effective_plan(access, stored) == expected


@pytest.mark.parametrize("stored", ["free", "pro"])
def test_admin_campaign_policy_is_premium_regardless_of_stored_plan(monkeypatch, stored):
    setup_db(monkeypatch, database(stored, "ADMIN"))
    policy = campaign_policy.load_campaign_policy("owner", "profile-a")
    assert policy.tier == "premium" and policy.is_admin
    assert policy.campaigns_enabled and policy.automation_enabled
    assert policy.active_campaigns_limit is None


def test_admin_limits_response_shows_premium_not_upgrade_prompt(monkeypatch):
    setup_db(monkeypatch, database("free", "ADMIN"))
    result = asyncio.run(campaigns.get_campaign_limits(user_id="owner", profile_id="profile-a"))
    assert result["plan_tier"] == "premium" and result["is_admin"] is True
    assert result["campaigns_enabled"] is True and result["automation_entitled"] is True


def test_regular_free_user_stays_free(monkeypatch):
    setup_db(monkeypatch, database("free", "USER"))
    policy = campaign_policy.load_campaign_policy("owner", "profile-a")
    assert policy.tier == "free" and not policy.campaigns_enabled

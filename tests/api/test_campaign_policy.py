"""F4C2: política server-side, limites e downgrade sem ativação."""
import asyncio
from datetime import date, time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException

from api import campaign_policy
from api.routers import campaigns
from conftest import FakeDB

DRAFT_ID = UUID("11111111-1111-1111-1111-111111111111")
POLICIES = [
    dict(tier="free", active_campaigns_per_profile=0, campaign_days=0,
         campaign_posts_per_day=0, automation_enabled=False),
    dict(tier="pro", active_campaigns_per_profile=2, campaign_days=15,
         campaign_posts_per_day=3, automation_enabled=False),
    dict(tier="premium", active_campaigns_per_profile=5, campaign_days=30,
         campaign_posts_per_day=15, automation_enabled=True),
]


def database(tier="pro", access="USER"):
    return FakeDB({
        "users": [dict(id="owner", access=access, plan_tier=tier)],
        "profiles": [dict(id="profile-a", user_id="owner"),
                     dict(id="profile-b", user_id="owner"),
                     dict(id="foreign", user_id="other")],
        "plan_limits": POLICIES,
        "campaign_drafts": [dict(
            id=str(DRAFT_ID), user_id="owner", profile_id="profile-a",
            status="draft", revision=1, source_list_id=11, items=[item()])],
    })


def item():
    return dict(product_id=12, title="Oferta", copy="", networks=["threads"])


def schedule(days=15, posts=3):
    start = date(2026, 11, 10)
    return campaigns.CampaignPreviewRequest(
        list_id=11, item_ids=[12], start_date=start,
        end_date=start + timedelta(days=days - 1), weekdays=list(range(7)),
        start_time=time(9), end_time=time(18), posts_per_day=posts)


def setup_db(monkeypatch, db):
    monkeypatch.setattr(campaign_policy, "supabase", db)
    monkeypatch.setattr(campaigns, "supabase", db)


@pytest.mark.parametrize("tier,enabled,limit,days,posts,automation", [
    ("free", False, 0, 0, 0, False),
    ("pro", True, 2, 15, 3, False),
    ("plus", True, 2, 15, 3, False),
    ("premium", True, 5, 30, 15, True),
])
def test_policy_uses_account_and_audited_catalog(
    monkeypatch, tier, enabled, limit, days, posts, automation,
):
    db = database(tier)
    # Etiqueta de perfil divergente não promove nem rebaixa a conta.
    db.tables["profiles"][0]["plan_tier"] = "premium" if tier == "free" else "free"
    setup_db(monkeypatch, db)
    policy = campaign_policy.load_campaign_policy("owner", "profile-a")
    assert (policy.campaigns_enabled, policy.active_campaigns_limit,
            policy.campaign_days, policy.campaign_posts_per_day,
            policy.automation_enabled) == (enabled, limit, days, posts, automation)


def test_admin_bypasses_commercial_caps_not_absolute_safety(monkeypatch):
    setup_db(monkeypatch, database("free", "ADMIN"))
    policy = campaign_policy.load_campaign_policy("owner", "profile-a")
    campaign_policy.validate_campaign_plan_schedule(policy, schedule(30, 15))
    campaign_policy.require_automation_access(policy)
    assert policy.active_campaigns_limit is None
    with pytest.raises(HTTPException) as caught:
        campaign_policy.validate_campaign_plan_schedule(policy, schedule(31))
    assert caught.value.status_code == 422


@pytest.mark.parametrize("tier,days,posts", [("pro", 16, 3), ("pro", 15, 4)])
def test_pro_rejects_excess_even_with_few_selected_weekdays(monkeypatch, tier, days, posts):
    setup_db(monkeypatch, database(tier))
    plan = schedule(days, posts)
    plan.weekdays = [1]
    with pytest.raises(HTTPException) as caught:
        campaign_policy.validate_campaign_plan_schedule(
            campaign_policy.load_campaign_policy("owner", "profile-a"), plan)
    assert caught.value.status_code == 403


@pytest.mark.parametrize("tier,days,posts", [("pro", 15, 3), ("premium", 30, 15)])
def test_plan_boundaries_are_inclusive(monkeypatch, tier, days, posts):
    setup_db(monkeypatch, database(tier))
    campaign_policy.validate_campaign_plan_schedule(
        campaign_policy.load_campaign_policy("owner", "profile-a"), schedule(days, posts))


@pytest.mark.parametrize("profile", ["foreign", "missing"])
@pytest.mark.parametrize("access", ["USER", "ADMIN"])
def test_ownership_never_bypassed(monkeypatch, profile, access):
    setup_db(monkeypatch, database("premium", access))
    with pytest.raises(HTTPException) as caught:
        campaign_policy.load_campaign_policy("owner", profile)
    assert caught.value.status_code == 404


@pytest.mark.parametrize("fault", ["db", "account_missing", "policy_missing", "invalid", "role"])
def test_unavailable_or_malformed_policy_fails_closed(monkeypatch, fault):
    db = database()
    if fault == "db":
        db = Mock()
        db.table.side_effect = RuntimeError("private database details")
    elif fault == "account_missing":
        db.tables["users"] = []
    elif fault == "policy_missing":
        db.tables["plan_limits"] = []
    elif fault == "invalid":
        db.tables["plan_limits"][1]["campaign_days"] = True
    else:
        db.tables["users"][0]["access"] = "admin-from-client"
    setup_db(monkeypatch, db)
    with pytest.raises(HTTPException) as caught:
        campaign_policy.load_campaign_policy("owner", "profile-a")
    assert caught.value.status_code == 503
    assert "private" not in caught.value.detail


def test_policy_changes_and_downgrade_are_not_cached(monkeypatch):
    db = database("premium")
    setup_db(monkeypatch, db)
    assert campaign_policy.load_campaign_policy("owner", "profile-a").automation_enabled
    db.tables["users"][0]["plan_tier"] = "pro"
    pro = campaign_policy.load_campaign_policy("owner", "profile-a")
    with pytest.raises(HTTPException):
        campaign_policy.validate_campaign_plan_schedule(pro, schedule(30, 15))
    with pytest.raises(HTTPException):
        campaign_policy.require_automation_access(pro)
    db.tables["plan_limits"][1]["campaign_posts_per_day"] = 2
    with pytest.raises(HTTPException):
        campaign_policy.validate_campaign_plan_schedule(
            campaign_policy.load_campaign_policy("owner", "profile-a"), schedule(15, 3))


@pytest.mark.parametrize("tier", ["free", "pro"])
def test_only_premium_or_admin_can_be_entitled_to_automation(monkeypatch, tier):
    db = database(tier)
    for row in db.tables["plan_limits"]:
        row["automation_enabled"] = True  # Não libera Pro/Free por flag incorreta.
    setup_db(monkeypatch, db)
    with pytest.raises(HTTPException) as caught:
        campaign_policy.require_automation_access(
            campaign_policy.load_campaign_policy("owner", "profile-a"))
    assert caught.value.status_code == 403


def test_limits_endpoint_is_read_only_scoped_and_honest(monkeypatch):
    db = database("premium")
    setup_db(monkeypatch, db)
    result = asyncio.run(campaigns.get_campaign_limits(user_id="owner", profile_id="profile-a"))
    assert result["active_campaigns_limit"] == 5
    assert result["active_campaigns_count"] is None
    assert result["activation_available"] is False
    assert result["automation_entitled"] is True
    assert result["automation_available"] is False
    assert len(db.tables["campaign_drafts"]) == 1
    with pytest.raises(HTTPException) as caught:
        asyncio.run(campaigns.get_campaign_limits(user_id="owner", profile_id="foreign"))
    assert caught.value.status_code == 404


@pytest.mark.parametrize("operation", ["preview", "create", "update", "upload"])
def test_free_blocks_all_growth_before_side_effects(monkeypatch, operation):
    db = database("free")
    setup_db(monkeypatch, db)
    forbidden = Mock(side_effect=AssertionError("Side effect before entitlement"))
    monkeypatch.setattr(campaigns, "_get_list", forbidden)
    monkeypatch.setattr(campaigns, "_read_media_content", forbidden)
    if operation == "preview":
        call = campaigns.preview_campaign(schedule(), user_id="owner", profile_id="profile-a")
    elif operation == "create":
        call = campaigns.create_campaign_draft(
            campaigns.CampaignDraftSave(name="Oferta", list_id=11, items=[item()]),
            user_id="owner", profile_id="profile-a")
    elif operation == "update":
        call = campaigns.update_campaign_draft(
            DRAFT_ID, campaigns.CampaignDraftUpdate(
                name="Oferta", expected_revision=1, items=[item()]),
            user_id="owner", profile_id="profile-a")
    else:
        call = campaigns.upload_campaign_media(
            DRAFT_ID, 12, file=object(), user_id="owner", profile_id="profile-a")
    with pytest.raises(HTTPException) as caught:
        asyncio.run(call)
    assert caught.value.status_code == 403
    forbidden.assert_not_called()
    assert len(db.tables["campaign_drafts"]) == 1
    assert db.tables["campaign_drafts"][0]["revision"] == 1


@pytest.mark.parametrize("operation", ["preview", "create", "update"])
@pytest.mark.parametrize("days,posts", [(16, 3), (15, 4)])
def test_route_cannot_bypass_pro_caps(monkeypatch, operation, days, posts):
    db = database()
    setup_db(monkeypatch, db)
    plan = schedule(days, posts)
    monkeypatch.setattr(campaigns, "_get_list", lambda *a: {"id": 11, "name": "Lista"})
    monkeypatch.setattr(campaigns, "_get_list_products", lambda *a: [{"id": 12}])
    if operation == "preview":
        call = campaigns.preview_campaign(plan, user_id="owner", profile_id="profile-a")
    elif operation == "create":
        call = campaigns.create_campaign_draft(
            campaigns.CampaignDraftSave(name="Oferta", list_id=11, items=[item()], schedule=plan),
            user_id="owner", profile_id="profile-a")
    else:
        call = campaigns.update_campaign_draft(
            DRAFT_ID, campaigns.CampaignDraftUpdate(
                name="Oferta", expected_revision=1, items=[item()], schedule=plan),
            user_id="owner", profile_id="profile-a")
    with pytest.raises(HTTPException) as caught:
        asyncio.run(call)
    assert caught.value.status_code == 403
    assert len(db.tables["campaign_drafts"]) == 1


def test_downgraded_free_can_read_and_delete_legacy_draft(monkeypatch):
    db = database("free")
    setup_db(monkeypatch, db)
    assert asyncio.run(campaigns.get_campaign_draft(
        DRAFT_ID, user_id="owner", profile_id="profile-a"))["id"] == str(DRAFT_ID)
    assert len(asyncio.run(campaigns.list_campaign_drafts(
        user_id="owner", profile_id="profile-a"))["data"]) == 1
    assert asyncio.run(campaigns.list_campaign_drafts(
        user_id="owner", profile_id="profile-b"))["data"] == []
    with pytest.raises(HTTPException) as caught:
        asyncio.run(campaigns.get_campaign_draft(
            DRAFT_ID, user_id="owner", profile_id="profile-b"))
    assert caught.value.status_code == 404
    db.storage = SimpleNamespace(from_=lambda bucket: None)
    asyncio.run(campaigns.delete_campaign_draft(
        DRAFT_ID, expected_revision=1, user_id="owner", profile_id="profile-a"))
    assert db.tables["campaign_drafts"] == []


def test_limits_auth_dependencies_and_no_activation_route():
    from api.routers.auth import get_current_user_id
    from api.routers.profiles import get_current_profile_id
    route = next(r for r in campaigns.router.routes if r.path == "/campaigns/limits")
    assert {d.call for d in route.dependant.dependencies} == {
        get_current_user_id, get_current_profile_id}
    assert not any("activat" in route.path for route in campaigns.router.routes)


@pytest.mark.parametrize("tier,slots,networks", [
    ("pro", 2, ["threads", "facebook"]),
    ("premium", 15, ["threads", "facebook"]),
])
@pytest.mark.parametrize("operation", ["create", "update"])
def test_each_network_counts_toward_daily_campaign_limit(
    monkeypatch, tier, slots, networks, operation,
):
    db = database(tier)
    setup_db(monkeypatch, db)
    monkeypatch.setattr(campaigns, "_get_list", lambda *a: {"id": 11, "name": "Lista"})
    monkeypatch.setattr(campaigns, "_get_list_products", lambda *a: [{"id": 12}])
    prepared = item()
    prepared["networks"] = networks
    plan = schedule(1, slots)
    if operation == "create":
        call = campaigns.create_campaign_draft(
            campaigns.CampaignDraftSave(
                name="Oferta", list_id=11, items=[prepared], schedule=plan),
            user_id="owner", profile_id="profile-a")
    else:
        call = campaigns.update_campaign_draft(
            DRAFT_ID, campaigns.CampaignDraftUpdate(
                name="Oferta", expected_revision=1, items=[prepared], schedule=plan),
            user_id="owner", profile_id="profile-a")
    with pytest.raises(HTTPException) as caught:
        asyncio.run(call)
    assert caught.value.status_code == 403
    assert "cada rede" in caught.value.detail
    assert db.tables["campaign_drafts"][0]["revision"] == 1


def test_drafts_do_not_consume_active_campaign_slots(monkeypatch):
    db = database("pro")
    setup_db(monkeypatch, db)
    monkeypatch.setattr(campaigns, "_get_list", lambda *a: {"id": 11, "name": "Lista"})
    monkeypatch.setattr(campaigns, "_get_list_products", lambda *a: [{"id": 12}])
    for index in range(3):
        asyncio.run(campaigns.create_campaign_draft(
            campaigns.CampaignDraftSave(
                name=f"Oferta {index}", list_id=11, items=[item()], schedule=schedule(15, 3)),
            user_id="owner", profile_id="profile-a"))
    assert len(db.tables["campaign_drafts"]) == 4
    result = asyncio.run(campaigns.get_campaign_limits(user_id="owner", profile_id="profile-a"))
    assert result["active_campaigns_count"] is None


def test_premium_catalog_flag_can_disable_automation(monkeypatch):
    db = database("premium")
    db.tables["plan_limits"][2]["automation_enabled"] = False
    setup_db(monkeypatch, db)
    with pytest.raises(HTTPException):
        campaign_policy.require_automation_access(
            campaign_policy.load_campaign_policy("owner", "profile-a"))


def test_daily_network_volume_follows_product_rotation_not_global_sum(monkeypatch):
    setup_db(monkeypatch, database("pro"))
    policy = campaign_policy.load_campaign_policy("owner", "profile-a")
    plan = schedule(3, 2)
    plan.item_ids = [12, 13, 14]
    prepared = [
        campaigns.CampaignDraftItem(**{**item(), "product_id": 12, "networks": ["threads", "facebook"]}),
        campaigns.CampaignDraftItem(**{**item(), "product_id": 13}),
        campaigns.CampaignDraftItem(**{**item(), "product_id": 14}),
    ]
    # Dias locais: A+B=3, C+A=3, B+C=2. Total 8 não viola limite diário 3.
    campaign_policy.validate_campaign_network_volume(policy, plan, prepared)
    prepared[2].networks = ["threads", "facebook"]
    # Segundo dia passa a C+A=4; não diluir o excesso em média de três dias.
    with pytest.raises(HTTPException) as caught:
        campaign_policy.validate_campaign_network_volume(policy, plan, prepared)
    assert caught.value.status_code == 403

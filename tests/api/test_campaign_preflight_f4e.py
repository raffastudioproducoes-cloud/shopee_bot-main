"""F4E-2A: preflight de leitura; reserva e despacho indisponíveis."""
import asyncio
import copy
import re
from datetime import date, timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException

from api import campaign_policy
from api.routers import campaigns
from conftest import FakeDB, _FakeTable

DRAFT = UUID("11111111-1111-1111-1111-111111111111")


def setup_db(monkeypatch, tier="pro", profile="profile-a", networks=None, revision=1):
    start = date.today() + timedelta(days=10)
    db = FakeDB({
        "users": [{"id": "owner", "access": "USER", "plan_tier": tier}],
        "profiles": [{"id": "profile-a", "user_id": "owner"}],
        "plan_limits": [
            {"tier": "pro", "active_campaigns_per_profile": 2, "campaign_days": 15,
             "campaign_posts_per_day": 3, "automation_enabled": False},
            {"tier": "free", "active_campaigns_per_profile": 0, "campaign_days": 0,
             "campaign_posts_per_day": 0, "automation_enabled": False},
        ],
        "campaign_drafts": [{
            "id": str(DRAFT), "user_id": "owner", "profile_id": profile,
            "status": "draft", "revision": revision, "source_list_id": 11,
            "items": [{"product_id": 12, "title": "Oferta", "copy": "",
                       "networks": networks if networks is not None else ["threads"]}],
            "schedule": {"list_id": 11, "item_ids": [12],
                         "start_date": start.isoformat(), "end_date": start.isoformat(),
                         "weekdays": [start.weekday()], "start_time": "09:00",
                         "end_time": "18:00", "posts_per_day": 2},
        }],
    })
    monkeypatch.setattr(campaigns, "supabase", db)
    monkeypatch.setattr(campaign_policy, "supabase", db)
    return db


def run(revision=1, profile="profile-a"):
    return asyncio.run(campaigns.preflight_campaign_draft(
        DRAFT, expected_revision=revision, user_id="owner", profile_id=profile))


def test_preflight_is_explicitly_not_a_reservation(monkeypatch):
    db = setup_db(monkeypatch)
    before = copy.deepcopy(db.tables)
    seen = []
    original_table = db.table
    def read_only_table(name):
        seen.append(name)
        assert name in {"users", "profiles", "plan_limits", "campaign_drafts"}
        return original_table(name)
    monkeypatch.setattr(db, "table", read_only_table)
    def forbidden(*args, **kwargs):
        raise AssertionError("preflight não pode escrever ou chamar RPC")
    for operation in ("insert", "update", "delete", "upsert"):
        monkeypatch.setattr(_FakeTable, operation, forbidden)
    monkeypatch.setattr(db, "rpc", forbidden, raising=False)
    result = run()
    assert db.tables == before
    assert set(seen) == {"users", "profiles", "plan_limits", "campaign_drafts"}
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", x)
               for x in result["planned_utc"])
    assert result["reservation_available"] is False
    assert result["reserved"] is False
    assert result["activated"] is False
    assert result["status"] == "preflight_only"
    assert result["checks_complete"] is False
    assert result["occurrence_count"] == 2


def test_preflight_rejects_other_profile_and_stale_revision(monkeypatch):
    setup_db(monkeypatch)
    with pytest.raises(HTTPException) as foreign:
        run(profile="profile-b")
    assert foreign.value.status_code == 404
    with pytest.raises(HTTPException) as stale:
        run(revision=2)
    assert stale.value.status_code == 409


def test_free_is_denied(monkeypatch):
    setup_db(monkeypatch, tier="free")
    with pytest.raises(HTTPException) as denied:
        run()
    assert denied.value.status_code == 403


def test_networks_count_toward_daily_limit(monkeypatch):
    setup_db(monkeypatch, networks=["threads", "instagram"])
    with pytest.raises(HTTPException) as denied:
        run()
    assert denied.value.status_code == 403


def test_empty_networks_and_past_schedule_are_rejected(monkeypatch):
    setup_db(monkeypatch, networks=[])
    with pytest.raises(HTTPException) as empty:
        run()
    assert empty.value.status_code == 422
    db = setup_db(monkeypatch)
    yesterday = date.today() - timedelta(days=1)
    schedule = db.tables["campaign_drafts"][0]["schedule"]
    schedule.update(start_date=yesterday.isoformat(), end_date=yesterday.isoformat(),
                    weekdays=[yesterday.weekday()])
    with pytest.raises(HTTPException) as past:
        run()
    assert past.value.status_code == 422

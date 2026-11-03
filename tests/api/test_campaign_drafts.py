"""F3A: contrato de rascunho persistente, sem ativar scheduler ou Storage."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.routers import campaigns


def item(product_id=12, **changes):
    values = dict(product_id=product_id, title="Produto", copy="",
                  affiliate_link="", networks=["threads"],
                  network_copies={"threads": ""}, use_shopee_image=True)
    values.update(changes)
    return values


def payload(**changes):
    values = dict(list_id=11, items=[item(12), item(13)],
                  schedule=None)
    values.update(changes)
    return campaigns.CampaignDraftSave(**values)


def test_draft_does_not_accept_ids_from_another_list_or_duplicates():
    with pytest.raises(ValueError, match="exatamente"):
        campaigns.validate_campaign_draft_items([item(12), item(999)], [12, 13])
    with pytest.raises(ValueError, match="repetições"):
        campaigns.validate_campaign_draft_items([item(12), item(12)], [12, 13])


def test_draft_preserves_intentionally_empty_copy_and_rejects_invalid_network():
    saved = payload()
    assert saved.items[0].copy == ""
    assert saved.items[0].network_copies["threads"] == ""
    with pytest.raises(Exception):
        payload(items=[item(12, networks=["kwai"]), item(13)])


class _InsertQuery:
    def __init__(self, records):
        self.records = records
        self.row = None

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        self.records.append(self.row)
        return SimpleNamespace(data=[{**self.row, "id": "draft-1", "revision": 1}])


class _DB:
    def __init__(self):
        self.writes = []
        self.table_names = []

    def table(self, name):
        self.table_names.append(name)
        return _InsertQuery(self.writes)


def test_create_draft_scopes_account_and_profile_without_creating_posts(monkeypatch):
    monkeypatch.setattr(campaigns, "_get_list",
                        lambda uid, lid, pid: {"id": lid, "name": "Minha lista",
                                               "user_id": uid, "profile_id": pid})
    monkeypatch.setattr(campaigns, "_get_list_products",
                        lambda lid: [{"id": 12, "image": "https://img.test/a"},
                                     {"id": 13, "image": "https://img.test/b"}])
    fake = _DB()
    monkeypatch.setattr(campaigns, "supabase", fake, raising=False)
    result = asyncio.run(campaigns.create_campaign_draft(payload(), user_id="owner", profile_id="profile-a"))
    assert result["id"] == "draft-1"
    assert fake.table_names == ["campaign_drafts"]
    assert fake.writes[0]["user_id"] == "owner"
    assert fake.writes[0]["profile_id"] == "profile-a"
    assert [x["product_id"] for x in fake.writes[0]["items"]] == [12, 13]


def test_create_draft_rejects_missing_profile_before_any_write(monkeypatch):
    fake = _DB()
    monkeypatch.setattr(campaigns, "supabase", fake, raising=False)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(campaigns.create_campaign_draft(payload(), user_id="owner", profile_id=None))
    assert caught.value.status_code == 400
    assert fake.writes == []

def test_schedule_must_match_saved_list_and_exact_product_order():
    schedule = campaigns.CampaignPreviewRequest(
        list_id=11, item_ids=[12, 13], start_date="2026-11-04",
        end_date="2026-11-06", weekdays=[0, 1, 2, 3, 4],
        start_time="09:00", end_time="18:00", interval_minutes=180,
    )
    campaigns.validate_campaign_draft_schedule(schedule, 11, [12, 13])
    with pytest.raises(ValueError, match="lista"):
        campaigns.validate_campaign_draft_schedule(schedule, 77, [12, 13])
    with pytest.raises(ValueError, match="ordem"):
        campaigns.validate_campaign_draft_schedule(schedule, 11, [13, 12])

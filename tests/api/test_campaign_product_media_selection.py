"""Selected product assets are account-owned, copied privately and never uploaded by the campaign UI."""
from contextlib import contextmanager
from uuid import UUID

import pytest
from fastapi import HTTPException

from conftest import FakeDB
from api.routers import campaigns
from api import campaign_product_media

ASSET = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
DRAFT = "33333333-3333-4333-8333-333333333333"
USER = "owner"
PROFILE = "profile-a"


def _asset(asset_id=ASSET, product_id=12, user_id=USER):
    return {"id": asset_id, "user_id": user_id, "product_id": product_id,
            "status": "ready", "media_type": "VIDEO", "mime_type": "video/mp4",
            "file_name": "filme.mp4", "size_bytes": 1024,
            "storage_key": f"products/{user_id}/{product_id}/{asset_id}.mp4"}


def _item(product_id=12, media_ids=None):
    return {"product_id": product_id, "title": "Oferta", "copy": "texto",
            "networks": ["threads"], "product_media_ids": media_ids or []}


class Storage:
    def __init__(self):
        self.copied = []
        self.removed = []

    def from_(self, bucket):
        assert bucket == "post-media"
        return self

    def copy(self, origin, target):
        self.copied.append((origin, target))

    def remove(self, paths):
        self.removed.extend(paths)


class StoreDB(FakeDB):
    def __init__(self, tables):
        super().__init__(tables)
        self.storage = Storage()


@contextmanager
def allow_capacity(_size):
    yield


def test_campaign_media_selection_accepts_only_ready_media_of_the_same_product_and_account(monkeypatch):
    fake = FakeDB({"product_media": [_asset(), _asset(OTHER, user_id="other")]})
    monkeypatch.setattr(campaigns, "supabase", fake)
    valid = campaigns.CampaignDraftItem.model_validate(_item(media_ids=[ASSET]))
    campaigns.validate_product_media_choices([valid], USER)
    for invalid in ([OTHER], ["44444444-4444-4444-8444-444444444444"]):
        with pytest.raises(HTTPException) as blocked:
            campaigns.validate_product_media_choices([
                campaigns.CampaignDraftItem.model_validate(_item(media_ids=invalid))], USER)
        assert blocked.value.status_code == 422
    with pytest.raises(HTTPException):
        campaigns.validate_product_media_choices([
            campaigns.CampaignDraftItem.model_validate(_item(product_id=999, media_ids=[ASSET]))], USER)
    with pytest.raises(ValueError):
        campaigns.CampaignDraftItem.model_validate(_item(media_ids=[ASSET, ASSET]))


def test_product_media_is_copied_only_on_activation_and_keeps_legacy_campaign_attachments(monkeypatch):
    legacy = {"id": "legacy", "user_id": USER, "profile_id": PROFILE, "campaign_id": DRAFT,
              "product_id": 12, "slot": 0, "status": "ready",
              "storage_key": f"campaigns/{USER}/{PROFILE}/{DRAFT}/12/legacy.jpg"}
    fake = StoreDB({"product_media": [_asset()], "campaign_draft_media": [legacy]})
    monkeypatch.setattr(campaign_product_media, "supabase", fake)
    monkeypatch.setattr(campaign_product_media, "storage_upload_reservation", allow_capacity)
    campaign_product_media.synchronize_product_media(DRAFT, USER, PROFILE, [_item(media_ids=[ASSET])])
    assert len(fake.storage.copied) == 1
    assert len(fake.tables["campaign_draft_media"]) == 2
    linked = next(row for row in fake.tables["campaign_draft_media"] if row["id"] != "legacy")
    assert linked["slot"] == 1
    assert linked["status"] == "ready"
    assert linked["storage_key"].startswith(f"campaigns/{USER}/{PROFILE}/{DRAFT}/12/linked/")
    assert linked["storage_key"].endswith(".mp4")
    campaign_product_media.synchronize_product_media(DRAFT, USER, PROFILE, [_item(media_ids=[ASSET])])
    assert len(fake.storage.copied) == 1  # retry is idempotent
    campaign_product_media.synchronize_product_media(DRAFT, USER, PROFILE, [_item(media_ids=[])])
    assert fake.tables["campaign_draft_media"] == [legacy]
    assert fake.storage.removed == [linked["storage_key"]]


def test_product_media_from_other_account_never_reaches_campaign_storage(monkeypatch):
    fake = StoreDB({"product_media": [_asset(user_id="other")], "campaign_draft_media": []})
    monkeypatch.setattr(campaign_product_media, "supabase", fake)
    monkeypatch.setattr(campaign_product_media, "storage_upload_reservation", allow_capacity)
    with pytest.raises(HTTPException) as denied:
        campaign_product_media.synchronize_product_media(DRAFT, USER, PROFILE, [_item(media_ids=[ASSET])])
    assert denied.value.status_code == 409
    assert not fake.storage.copied


def test_media_id_determinism_is_scoped_to_each_campaign():
    assert UUID(campaign_product_media._linked_id(DRAFT, ASSET))
    assert campaign_product_media._linked_id(DRAFT, ASSET) == campaign_product_media._linked_id(DRAFT, ASSET)
    assert campaign_product_media._linked_id(DRAFT, ASSET) != campaign_product_media._linked_id(
        "55555555-5555-4555-8555-555555555555", ASSET)

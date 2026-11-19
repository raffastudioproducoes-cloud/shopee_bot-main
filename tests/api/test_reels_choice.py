"""Escolha "Publicar como Reels": validação por rede, gravação na head do Facebook
(posts.tiktok_options, sem coluna nova) e no item da campanha. Sem rede real."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.campaigns import CampaignDraftItem
from api.routers.profiles import get_current_profile_id

SCHEDULE = {"trigger": "cron", "time": "10:00", "days_of_week": [0]}


@pytest.fixture
def api(fake_db, monkeypatch):
    db = fake_db({"posts": [], "medias": [], "posts_medias": [], "posts_products": [], "products": []})
    monkeypatch.setattr(posts_module, "supabase", db)

    async def fake_job(**_kw):
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    monkeypatch.setattr(posts_module, "_preview_batch", lambda body, drafts, x=True: [
        {"network": c.network, "texts": c.texts[:1], "mode": "video", "media_draft_ids": [],
         "warnings": [], "blocked_reason": None, "dropped": []} for c in body.compositions
    ])
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield TestClient(app), db
    app.dependency_overrides.clear()


def _batch(compositions):
    return {"compositions": compositions, "schedule": SCHEDULE}


def test_facebook_choice_is_stored_on_head_only(api):
    client, db = api
    res = client.post("/posts/batch", json=_batch([
        {"network": "facebook", "texts": ["oi"], "reels": True},
        {"network": "instagram", "texts": ["oi"], "reels": True},
        {"network": "threads", "texts": ["oi"]},
    ]))
    assert res.status_code == 201, res.text
    heads = {row["network"]: row for row in db.tables["posts"]}
    assert heads["facebook"]["tiktok_options"]["reels"] is True
    assert heads["facebook"]["tiktok_options"]["confirmed_at"]
    assert "tiktok_options" not in heads["instagram"]  # Instagram já é sempre Reels
    assert "tiktok_options" not in heads["threads"]


def test_facebook_off_is_stored_and_absent_keeps_old_behavior(api):
    client, db = api
    assert client.post("/posts/batch", json=_batch([
        {"network": "facebook", "texts": ["oi"], "reels": False}])).status_code == 201
    assert db.tables["posts"][0]["tiktok_options"] == {"reels": False, "confirmed_at": db.tables["posts"][0]["tiktok_options"]["confirmed_at"]}
    db.tables["posts"].clear()
    assert client.post("/posts/batch", json=_batch([{"network": "facebook", "texts": ["oi"]}])).status_code == 201
    assert "tiktok_options" not in db.tables["posts"][0]


@pytest.mark.parametrize("composition,message", [
    ({"network": "threads", "texts": ["oi"], "reels": True}, "Facebook e Instagram"),
    ({"network": "instagram", "texts": ["oi"], "reels": False}, "sempre publicado como Reels"),
])
def test_invalid_reels_choice_is_422_and_creates_nothing(api, composition, message):
    client, db = api
    res = client.post("/posts/batch", json=_batch([composition]))
    assert res.status_code == 422 and message in res.text
    assert db.tables["posts"] == []


def test_campaign_item_accepts_facebook_reels():
    item = CampaignDraftItem.model_validate({
        "product_id": 1, "title": "t", "copy": "c", "networks": ["facebook"], "facebook_reels": True})
    assert item.model_dump(mode="json", by_alias=True)["facebook_reels"] is True
    legacy = CampaignDraftItem.model_validate({"product_id": 1, "title": "t", "copy": "c"})
    assert legacy.facebook_reels is None

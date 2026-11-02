"""Escopo OAuth do X gravado e usado para liberar (ou não) imagens."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api import x_oauth
from api.main import app
from api.routers import credentials as cred
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id

FULL = "tweet.read tweet.write users.read media.write offline.access"
NO_MEDIA = "tweet.read tweet.write users.read offline.access"


def test_has_media_write_unknown_or_missing_is_false():
    assert x_oauth.has_media_write(FULL) is True
    assert x_oauth.has_media_write(NO_MEDIA) is False
    assert x_oauth.has_media_write(None) is False
    assert x_oauth.has_media_write("") is False
    assert x_oauth.has_media_write("xmedia.write") is False


def _callback(monkeypatch, token_data):
    saved = {}

    async def fake_exchange(code, verifier):
        return token_data

    monkeypatch.setattr(cred.x_oauth, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(cred, "_upsert_by_user", lambda t, u, data, profile_id=None: saved.update(data))
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    client = TestClient(app)
    state, cookie = cred._sign_oauth_state(42, {"code_verifier": "v"})
    client.cookies.set("x_oauth_state", cookie)
    res = client.get("/credentials/x/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert res.status_code == 307
    return saved


def test_callback_persists_granted_scope(monkeypatch):
    saved = _callback(monkeypatch, {"access_token": "a", "refresh_token": "r", "scope": NO_MEDIA})
    assert saved["scope"] == NO_MEDIA


def test_callback_without_scope_stores_null(monkeypatch):
    saved = _callback(monkeypatch, {"access_token": "a", "refresh_token": "r"})
    assert saved["scope"] is None


@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "users": [{"id": 42, "access": "USER"}],
        "x_credentials": [{
            "id": 1, "user_id": 42, "profile_id": "profile-a", "status": True,
            "user_access_token": cred.encrypt("tok"), "user_refresh_token": cred.encrypt("ref"),
            "scope": FULL,
        }],
    })
    monkeypatch.setattr(cred, "supabase", database)
    monkeypatch.setattr(posts_module, "supabase", database)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield database
    app.dependency_overrides.clear()


@pytest.mark.parametrize("scope,supports,missing", [
    (FULL, True, []),
    (NO_MEDIA, False, ["media.write"]),
    (None, False, ["media.write"]),
])
def test_list_credentials_exposes_x_media_support(db, scope, supports, missing):
    db.tables["x_credentials"][0]["scope"] = scope
    x = TestClient(app).get("/credentials").json()["x"]
    assert x["supports_media"] is supports
    assert x["missing_scopes"] == missing
    assert "tok" not in str(x) and "scope" not in x


def test_disconnected_x_has_no_scope_warning(db):
    db.tables["x_credentials"][0].update(user_access_token=None, scope=None)
    x = TestClient(app).get("/credentials").json()["x"]
    assert x["connected"] is False
    assert x["supports_media"] is False and x["missing_scopes"] == []


def test_refreshed_tokens_persist_new_scope(db):
    cred._persist_refreshed_tokens(
        "x", 42, "profile-a", {"access_token": "n", "refresh_token": "nr", "scope": NO_MEDIA},
    )
    assert db.tables["x_credentials"][0]["scope"] == NO_MEDIA


def test_refreshed_tokens_without_scope_keep_previous(db):
    cred._persist_refreshed_tokens("x", 42, "profile-a", {"access_token": "n", "refresh_token": "nr"})
    assert db.tables["x_credentials"][0]["scope"] == FULL


def test_disconnect_clears_scope(db):
    assert TestClient(app).delete("/credentials/x").status_code == 200
    assert db.tables["x_credentials"][0]["scope"] is None


# --- preview / batch --------------------------------------------------------
def _batch_client(db, monkeypatch):
    db.tables["temporary_media_uploads"] = [{
        "id": "11111111-1111-4111-8111-111111111111", "user_id": 42, "profile_id": "profile-a", "status": "ready",
        "storage_bucket": "post-media", "storage_key": "drafts/offer.jpg",
        "file_name": "offer.jpg", "size_bytes": 12, "media_type": "IMAGE",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }]

    async def fake_job(**_kw):
        return "job"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    return TestClient(app)


BODY = {
    "compositions": [{"network": "x", "texts": ["copy"]}, {"network": "threads", "texts": ["copy"]}],
    "draft_media_ids": ["11111111-1111-4111-8111-111111111111"],
    "schedule": {"trigger": "cron", "time": "10:00", "days_of_week": [0]},
}


@pytest.mark.parametrize("scope", [NO_MEDIA, None])
def test_preview_blocks_x_image_without_media_write(db, monkeypatch, scope):
    db.tables["x_credentials"][0]["scope"] = scope
    plans = {p["network"]: p for p in _batch_client(db, monkeypatch).post("/posts/preview", json=BODY).json()["plans"]}
    assert plans["x"]["mode"] == "blocked"
    assert "reconecte o X" in plans["x"]["blocked_reason"]
    assert plans["x"]["media_draft_ids"] == []
    assert plans["threads"]["mode"] == "single_image"


def test_preview_allows_x_image_with_media_write(db, monkeypatch):
    plans = {p["network"]: p for p in _batch_client(db, monkeypatch).post("/posts/preview", json=BODY).json()["plans"]}
    assert plans["x"]["mode"] == "single_image"


def test_batch_does_not_create_blocked_x_post(db, monkeypatch):
    db.tables["x_credentials"][0]["scope"] = NO_MEDIA
    res = _batch_client(db, monkeypatch).post("/posts/batch", json=BODY)
    assert res.status_code == 201
    assert [c["network"] for c in res.json()["created"]] == ["threads"]
    assert [b["network"] for b in res.json()["blocked"]] == ["x"]


def test_text_only_x_post_does_not_need_media_write(db, monkeypatch):
    db.tables["x_credentials"][0]["scope"] = None
    body = {**BODY, "draft_media_ids": [], "compositions": [{"network": "x", "texts": ["copy"]}]}
    plan = _batch_client(db, monkeypatch).post("/posts/preview", json=body).json()["plans"][0]
    assert plan["mode"] != "blocked"

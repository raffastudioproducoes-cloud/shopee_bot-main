"""Backup de catálogo por conta e conteúdo operacional por perfil."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import lists as lists_module
from api.routers import posts as posts_module
from api.routers import users as users_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def env(fake_db, monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    db = fake_db({
        "products": [
            {"id": 1, "user_id": 42, "product_id": "111", "name": "Compartilhado", "original_link": "https://example.invalid/original", "commission_link": "https://example.invalid/commission"},
        ],
        "product_lists": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "name": "Lista A"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "name": "Lista B"},
        ],
        "posts": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "text": "post A", "post_id": None, "network": "threads"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "text": "post B", "post_id": None, "network": "threads"},
        ],
    })
    for module in (users_module, lists_module, posts_module):
        monkeypatch.setattr(module, "supabase", db)

    def _client(cookie=None):
        c = TestClient(app)
        if cookie:
            c.cookies.update(cookie)
        return c

    yield db, _client
    app.dependency_overrides.clear()


def test_export_contains_shared_catalog_and_active_profile_data(env, profile_cookie):
    _db, client = env
    body = client(profile_cookie("profile-a")).get("/users/me/backup").json()
    assert [p["name"] for p in body["products"]] == ["Compartilhado"]
    assert [p["name"] for p in body["product_lists"]] == ["Lista A"]
    assert [p["texts"] for p in body["posts"]] == [["post A"]]
    assert body["source_profile_id"] == "profile-a"


def test_export_without_profile_contains_only_shared_catalog(env, old_token_without_profile_claim):
    _db, client = env
    body = client(old_token_without_profile_claim).get("/users/me/backup").json()
    assert [p["name"] for p in body["products"]] == ["Compartilhado"]
    assert body["product_lists"] == []
    assert body["posts"] == []
    assert "source_profile_id" not in body


def test_restore_rejects_isolated_data_from_another_profile_before_writing(env, profile_cookie):
    db, client = env
    backup = client(profile_cookie("profile-a")).get("/users/me/backup").json()
    res = client(profile_cookie("profile-c")).post("/users/me/restore", json=backup)
    assert res.status_code == 400
    assert "outro perfil" in res.json()["detail"]
    assert [p for p in db.tables["product_lists"] if p["id"] > 1000] == []
    assert [p for p in db.tables["posts"] if p["id"] > 1000] == []


def test_restore_into_matching_profile_keeps_isolated_data_scoped(env, profile_cookie):
    db, client = env
    backup = client(profile_cookie("profile-a")).get("/users/me/backup").json()
    assert client(profile_cookie("profile-a")).post("/users/me/restore", json=backup).status_code == 200
    assert [p["profile_id"] for p in db.tables["product_lists"] if p["id"] > 1000] == ["profile-a"]
    assert [p["profile_id"] for p in db.tables["posts"] if p["id"] > 1000] == ["profile-a"]
    assert "profile_id" not in db.tables["products"][0]


def test_restore_legacy_catalog_only_backup_is_accepted(env, profile_cookie):
    db, client = env
    payload = {
        "products": [{"id": 9, "product_id": "999", "name": "Antigo", "original_link": "https://example.invalid/original", "commission_link": "https://example.invalid/commission"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum({k: v for k, v in payload.items()})
    assert client(profile_cookie("profile-b")).post("/users/me/restore", json=payload).status_code == 200
    created = [p for p in db.tables["products"] if p["id"] > 1000]
    assert "profile_id" not in created[0]


def test_restore_legacy_backup_without_marker_rejects_isolated_content(env, profile_cookie):
    db, client = env
    payload = {
        "products": [],
        "product_lists": [{"name": "Lista antiga", "product_ids": []}],
        "posts": [],
        "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum(dict(payload))

    response = client(profile_cookie("profile-a")).post("/users/me/restore", json=payload)

    assert response.status_code == 400
    assert "outro perfil" in response.json()["detail"]
    assert [p for p in db.tables["product_lists"] if p["id"] > 1000] == []


def test_restore_catalog_updates_shared_product_without_copying_per_profile(env, profile_cookie):
    db, client = env
    payload = {
        "products": [{"id": 1, "product_id": "111", "name": "Copia em B", "original_link": "https://example.invalid/original", "commission_link": "https://example.invalid/commission"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum(dict(payload))
    assert client(profile_cookie("profile-b")).post("/users/me/restore", json=payload).status_code == 200
    rows = [p for p in db.tables["products"] if p["product_id"] == "111"]
    assert [p["name"] for p in rows] == ["Copia em B"]
    assert "profile_id" not in rows[0]


def test_restore_updates_existing_product_of_same_profile_instead_of_duplicating(env, profile_cookie):
    db, client = env
    payload = {
        "products": [{"id": 1, "product_id": "111", "name": "Renomeado", "original_link": "https://example.invalid/original", "commission_link": "https://example.invalid/commission"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum(dict(payload))
    assert client(profile_cookie("profile-a")).post("/users/me/restore", json=payload).status_code == 200
    assert [p["name"] for p in db.tables["products"] if p["product_id"] == "111"] == ["Renomeado"]
    assert len(db.tables["products"]) == 1


def test_restore_shared_catalog_without_profile_is_allowed(env, old_token_without_profile_claim):
    db, client = env
    payload = {
        "products": [{"id": 9, "product_id": "999", "name": "Sem perfil", "original_link": "https://example.invalid/original", "commission_link": "https://example.invalid/commission"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum(dict(payload))
    assert client(old_token_without_profile_claim).post("/users/me/restore", json=payload).status_code == 200
    created = [p for p in db.tables["products"] if p["id"] > 1000]
    assert "profile_id" not in created[0]

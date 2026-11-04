"""Multi-perfil: catálogo é da conta; recursos operacionais respeitam o perfil ativo."""
import pytest
from fastapi.testclient import TestClient

from api.crypto import encrypt
from api.main import app
from api.routers import catalog as catalog_module
from api.routers import dashboard as dashboard_module
from api.routers import notifications as notifications_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def env(fake_db, monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    db = fake_db({
        "products": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b"},
            {"id": 3, "user_id": 42, "profile_id": "profile-b"},
        ],
        "product_lists": [{"id": 1, "user_id": 42, "profile_id": "profile-b"}],
        "posts": [{"id": 1, "user_id": 42, "profile_id": "profile-a", "post_id": None}],
        "schedulers": [{"id": "s1", "user_id": 42, "profile_id": "profile-b"}],
        "activities": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "metadata": {}, "created_at": "2026-01-01"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "metadata": {}, "created_at": "2026-01-02"},
        ],
        "shopee_credentials": [
            {"id": 1, "user_id": 42, "profile_id": None, "app_id": "app-a", "secret": encrypt("sec-a")},
        ],
    })
    for module in (dashboard_module, notifications_module, catalog_module):
        monkeypatch.setattr(module, "supabase", db)
    yield db
    app.dependency_overrides.clear()


def _client(cookie):
    c = TestClient(app)
    c.cookies.update(cookie)
    return c


def test_dashboard_counts_whole_account_regardless_of_active_profile(env, profile_cookie):
    expected_counts = {
        "products_count": 3,
        "posts_count": 1,
        "lists_count": 1,
        "scheduled_posts": 1,
    }
    for active_profile in ("profile-a", "profile-b"):
        stats = _client(profile_cookie(active_profile)).get("/dashboard/stats").json()
        assert {key: stats[key] for key in expected_counts} == expected_counts
        assert [item["id"] for item in stats["recent_posts"]] == [1]
        assert {item["id"] for item in stats["recent_activities"]} == {1, 2}


def test_dashboard_without_profile_counts_whole_account(env, old_token_without_profile_claim):
    stats = _client(old_token_without_profile_claim).get("/dashboard/stats").json()
    assert stats["products_count"] == 3 and stats["posts_count"] == 1


def test_notifications_only_active_profile(env, profile_cookie):
    data = _client(profile_cookie("profile-a")).get("/notifications").json()["data"]
    assert [n["id"] for n in data] == [1]


def test_notifications_without_profile_fallback(env, old_token_without_profile_claim):
    data = _client(old_token_without_profile_claim).get("/notifications").json()["data"]
    assert {n["id"] for n in data} == {1, 2}


def test_catalog_uses_account_credential_from_every_profile(env, profile_cookie, monkeypatch):
    seen = {}

    async def fake_search(app_id, secret, **_kw):
        seen["cred"] = (app_id, secret)
        return []

    monkeypatch.setattr(catalog_module.shopee_catalog, "search_products", fake_search)

    assert _client(profile_cookie("profile-a")).get("/products/catalog-search").status_code == 200
    assert seen["cred"] == ("app-a", "sec-a")

    assert _client(profile_cookie("profile-b")).get("/products/catalog-search").status_code == 200
    assert seen["cred"] == ("app-a", "sec-a")

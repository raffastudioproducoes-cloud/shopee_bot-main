"""Contrato novo: IA da plataforma, não credencial particular dos clientes."""

import httpx
import pytest
from fastapi.testclient import TestClient

from api.crypto import decrypt, encrypt
from api.main import app
from api.routers import credentials, platform_ai, posts
from api.routers.auth import get_current_user_id
from apis import llm


SECRET = "gemini-global-test-secret"


@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "users": [{"id": 7, "access": "ADMIN"}, {"id": 42, "access": "USER"}],
        "products": [{"id": 1, "user_id": 42, "name": "Caneca",
                      "commission": 12, "commission_link": "https://shopee.test/1"}],
        "ai_credentials": [{"user_id": 42, "provider": "gemini", "secret": encrypt("user-old-key"),
                            "status": True}],
        "platform_ai_credentials": [{"environment": "production", "provider": "gemini", "secret": encrypt(SECRET),
                                     "model": "gemini-3.5-flash-lite", "status": True,
                                     "check_state": "untested"}],
        "platform_ai_settings": [{"environment": "production", "active_provider": "gemini"}],
    })
    monkeypatch.setattr(credentials, "supabase", database)
    monkeypatch.setattr(platform_ai, "supabase", database)
    monkeypatch.setattr(posts, "supabase", database)
    monkeypatch.setattr(credentials, "log_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(platform_ai, "log_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(platform_ai, "_autotest_submit", lambda *args: None)
    return database


@pytest.fixture
def session():
    app.dependency_overrides.clear()
    def client_for(user_id):
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        return TestClient(app)
    yield client_for
    app.dependency_overrides.clear()


def test_client_sees_only_service_availability_not_secrets(db, session):
    client = session(42)
    res = client.get("/ai/status")
    assert res.status_code == 200
    assert res.json() == {"available": True}
    assert SECRET not in res.text and "provider" not in res.text


def test_user_cannot_manage_or_test_platform_key(db, session):
    client = session(42)
    assert client.get("/admin/ai").status_code == 403
    assert client.put("/admin/ai/gemini", json={"api_key": "new-key"}).status_code == 403
    assert client.post("/admin/ai/gemini/test").status_code == 403
    assert client.post("/admin/ai/gemini/activate").status_code == 403
    assert client.delete("/admin/ai/gemini").status_code == 403
    assert client.put("/credentials/ai/gemini", json={"api_key": "replacement"}).status_code == 403
    assert decrypt(db.tables["platform_ai_credentials"][0]["secret"]) == SECRET


def test_generation_uses_platform_key_for_other_accounts(db, session, monkeypatch):
    calls = []
    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append((url, headers))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Texto pronto"}]}}]})
    monkeypatch.setattr(llm.httpx, "post", fake_post)
    client = session(42)
    res = client.post("/posts/generate-copy", json={"product_id": 1, "provider": "openai"})
    assert res.status_code == 200
    assert res.json()["text"] == "Texto pronto"
    assert calls[0][1]["x-goog-api-key"] == SECRET
    assert "user-old-key" not in repr(calls) and SECRET not in res.text


def test_admin_can_rotate_and_activate_saved_providers(db, session, monkeypatch):
    client = session(7)
    monkeypatch.setattr(credentials, "_autotest_submit", lambda *args: None)
    res = client.put("/admin/ai/openai", json={"api_key": "new-openai", "model": "gpt-6-luna"})
    assert res.status_code == 200
    saved = next(row for row in db.tables["platform_ai_credentials"] if row["provider"] == "openai")
    assert decrypt(saved["secret"]) == "new-openai"
    assert client.get("/admin/ai").json()["active"] == "openai"
    assert SECRET not in client.get("/admin/ai").text

    res = client.post("/admin/ai/gemini/activate")
    assert res.status_code == 200
    assert client.get("/admin/ai").json()["active"] == "gemini"


def test_admin_disconnect_blocks_service_when_active(db, session):
    client = session(7)
    assert client.delete("/admin/ai/gemini").status_code == 200
    assert client.get("/ai/status").json() == {"available": False}
    assert client.get("/admin/ai").json()["active"] is None


def test_admin_invalid_model_is_rejected(db, session):
    client = session(7)
    response = client.put("/admin/ai/gemini", json={"api_key": "new", "model": "../invalid"})
    assert response.status_code == 400


def test_missing_global_key_returns_service_error_without_user_registration_hint(db, session):
    db.tables["platform_ai_settings"][0]["active_provider"] = None
    client = session(42)
    response = client.post("/posts/generate-copy", json={"product_id": 1})
    assert response.status_code == 503
    assert "Credenciais" not in response.text


def test_admin_staging_cannot_rotate_production_key(db, session, monkeypatch):
    db.tables["platform_ai_settings"].append({"environment": "staging", "active_provider": "gemini"})
    db.tables["platform_ai_credentials"].append({
        "environment": "staging", "provider": "gemini", "secret": encrypt(SECRET),
        "status": True,
    })
    monkeypatch.setattr(platform_ai, "current_environment", lambda: "staging")
    client = session(7)
    assert client.put("/admin/ai/gemini", json={"api_key": "staging-only"}).status_code == 200
    staging_key = next(row for row in db.tables["platform_ai_credentials"] if row["environment"] == "staging")
    prod_key = next(row for row in db.tables["platform_ai_credentials"] if row["environment"] == "production")
    assert decrypt(staging_key["secret"]) == "staging-only"
    assert decrypt(prod_key["secret"]) == SECRET

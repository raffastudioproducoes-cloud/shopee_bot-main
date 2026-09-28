"""
Testes do OAuth do TikTok (api/routers/credentials.py).

App único da plataforma (migração 2026-09-28 — TIKTOK_CLIENT_KEY/SECRET
via env, não mais por usuário): mesma estrutura de
tests/api/test_threads_oauth.py, sem precisar mockar credencial salva
antes do authorize/callback.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import credentials as credentials_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


def test_tiktok_authorize_returns_url_and_sets_state_cookie(client, monkeypatch):
    monkeypatch.setattr(credentials_module.tiktok_oauth, "CLIENT_KEY", "client-key-123")

    res = client.get("/credentials/tiktok/authorize")

    assert res.status_code == 200
    assert "client-key-123" in res.json()["url"]
    assert "state=" in res.json()["url"]
    assert "tiktok_oauth_state" in res.cookies


def test_tiktok_callback_success_saves_credential_and_redirects(client, monkeypatch):
    saved = {}

    async def fake_get_user_auth_id_token(code):
        assert code == "tiktok-code-123"
        return "user-access-token", "refresh-token", "open-id-1"

    def fake_upsert(table, user_id, data):
        saved["table"] = table
        saved["user_id"] = user_id
        saved["data"] = data
        return {**data, "id": 1}

    monkeypatch.setattr(
        credentials_module.tiktok_oauth,
        "get_user_auth_id_token",
        fake_get_user_auth_id_token,
    )
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    # simula o cookie assinado que /authorize teria gravado
    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("tiktok_oauth_state", cookie_value)

    res = client.get(
        "/credentials/tiktok/callback",
        params={"code": "tiktok-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "tiktok=success" in res.headers["location"]
    assert saved["table"] == "tiktok_credentials"
    assert saved["user_id"] == 42
    assert saved["data"]["open_id"] == "open-id-1"
    assert saved["data"]["status"] is True
    # token nunca é gravado em texto puro
    assert saved["data"]["user_access_token"] != "user-access-token"


def test_tiktok_callback_error_from_tiktok_redirects_without_saving(client, monkeypatch):
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/tiktok/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "tiktok=error" in res.headers["location"]
    assert upsert_called is False


def test_tiktok_callback_missing_state_redirects_without_saving(client, monkeypatch):
    """Sem cookie de state (ex.: callback acessado direto) — mesmo com
    `code` válido, não pode trocar por token (CSRF do account-linking)."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/tiktok/callback",
        params={"code": "tiktok-code-123"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "tiktok=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_tiktok_callback_state_mismatch_redirects_without_saving(client, monkeypatch):
    """Cookie presente mas `state` da query não bate — cenário de
    account-linking CSRF descrito no HIGH."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    _, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("tiktok_oauth_state", cookie_value)

    res = client.get(
        "/credentials/tiktok/callback",
        params={"code": "tiktok-code-123", "state": "attacker-controlled-state"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "tiktok=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_tiktok_authorize_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get("/credentials/tiktok/authorize")
    assert res.status_code == 401


def test_tiktok_callback_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get(
        "/credentials/tiktok/callback", params={"code": "x"}
    )
    assert res.status_code == 401

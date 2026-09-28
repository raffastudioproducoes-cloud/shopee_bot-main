"""
Testes do fluxo OAuth do Instagram (api/routers/credentials.py).

Mesmo padrão de tests/api/test_tiktok_oauth.py: o App ID/Secret do
Instagram é por usuário (tabela instagram_credentials, não env var
global) — authorize/callback primeiro leem a credencial já salva
(`_get_instagram_credentials_row`, mockada aqui em vez do Supabase de
verdade) antes de trocar code por token (api/instagram_oauth.py).

Cobre o caminho feliz de authorize/callback, o caso de erro vindo do
Meta (?error=), a falta de credencial salva, e a validação do `state`
(CSRF do account-linking).
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


def test_instagram_authorize_without_saved_app_id_fails_clearly(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module, "_get_instagram_credentials_row", lambda user_id: None
    )

    res = client.get("/credentials/instagram/authorize")

    assert res.status_code == 400


def test_instagram_authorize_returns_url_with_saved_app_id(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module,
        "_get_instagram_credentials_row",
        lambda user_id: {"app_id": "meta-app-123", "secret": "enc-secret"},
    )

    res = client.get("/credentials/instagram/authorize")

    assert res.status_code == 200
    assert "meta-app-123" in res.json()["url"]
    assert "state=" in res.json()["url"]
    assert "instagram_oauth_state" in res.cookies


def test_instagram_callback_success_saves_credential_and_redirects(client, monkeypatch):
    saved = {}

    monkeypatch.setattr(
        credentials_module,
        "_get_instagram_credentials_row",
        lambda user_id: {"app_id": "meta-app-123", "secret": "enc-secret"},
    )
    monkeypatch.setattr(credentials_module, "decrypt", lambda v: "plain-secret")

    async def fake_get_user_auth_id_token(app_id, secret, code):
        assert app_id == "meta-app-123"
        assert secret == "plain-secret"
        assert code == "meta-code-123"
        return "ig-business-1", "long-lived-token"

    def fake_upsert(table, user_id, data):
        saved["table"] = table
        saved["user_id"] = user_id
        saved["data"] = data
        return {**data, "id": 1}

    monkeypatch.setattr(
        credentials_module.instagram_oauth,
        "get_user_auth_id_token",
        fake_get_user_auth_id_token,
    )
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    # simula o cookie assinado que /authorize teria gravado
    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("instagram_oauth_state", cookie_value)

    res = client.get(
        "/credentials/instagram/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "instagram=success" in res.headers["location"]
    assert saved["table"] == "instagram_credentials"
    assert saved["user_id"] == 42
    assert saved["data"]["ig_user_id"] == "ig-business-1"
    assert saved["data"]["status"] is True
    # token nunca é gravado em texto puro
    assert saved["data"]["user_access_token"] != "long-lived-token"


def test_instagram_callback_error_from_meta_redirects_without_saving(client, monkeypatch):
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/instagram/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "instagram=error" in res.headers["location"]
    assert upsert_called is False


def test_instagram_callback_oauth_failure_redirects_without_saving(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module,
        "_get_instagram_credentials_row",
        lambda user_id: {"app_id": "meta-app-123", "secret": "enc-secret"},
    )
    monkeypatch.setattr(credentials_module, "decrypt", lambda v: "plain-secret")

    async def fake_get_user_auth_id_token(app_id, secret, code):
        raise credentials_module.instagram_oauth.InstagramOAuthError("no linked ig account")

    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(
        credentials_module.instagram_oauth,
        "get_user_auth_id_token",
        fake_get_user_auth_id_token,
    )
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("instagram_oauth_state", cookie_value)

    res = client.get(
        "/credentials/instagram/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "instagram=error" in res.headers["location"]
    assert "oauth_failed" in res.headers["location"]
    assert upsert_called is False


def test_instagram_callback_without_saved_client_credentials_fails_clearly(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module, "_get_instagram_credentials_row", lambda user_id: None
    )

    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("instagram_oauth_state", cookie_value)

    res = client.get(
        "/credentials/instagram/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "instagram=error" in res.headers["location"]
    assert "missing_client_credentials" in res.headers["location"]


def test_instagram_callback_missing_state_redirects_without_saving(client, monkeypatch):
    """Sem cookie de state (ex.: callback acessado direto) — mesmo com
    `code` válido, não pode trocar por token (CSRF do account-linking)."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/instagram/callback",
        params={"code": "meta-code-123"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "instagram=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_instagram_callback_state_mismatch_redirects_without_saving(client, monkeypatch):
    """Cookie presente mas `state` da query não bate com o do
    /authorize — cenário de account-linking CSRF descrito no HIGH."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    _, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("instagram_oauth_state", cookie_value)

    res = client.get(
        "/credentials/instagram/callback",
        params={"code": "meta-code-123", "state": "attacker-controlled-state"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "instagram=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_instagram_authorize_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get("/credentials/instagram/authorize")
    assert res.status_code == 401


def test_instagram_callback_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get(
        "/credentials/instagram/callback", params={"code": "x"}
    )
    assert res.status_code == 401

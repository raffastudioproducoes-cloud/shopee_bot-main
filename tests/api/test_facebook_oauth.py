"""
Testes do fluxo OAuth do Facebook (api/routers/credentials.py).

App único da plataforma, reaproveitando o mesmo app do Instagram (ver
api/facebook_oauth.py) — mesma estrutura de tests/api/test_instagram_oauth.py,
sem precisar mockar credencial salva antes do authorize/callback.
"""

import asyncio
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from api import facebook_oauth
from api.main import app
from api.routers import credentials as credentials_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


def test_facebook_authorize_returns_url_and_sets_state_cookie(client, monkeypatch):
    monkeypatch.setattr(credentials_module.instagram_oauth, "APP_ID", "app")
    monkeypatch.setattr(credentials_module.instagram_oauth, "SECRET", "sec")
    monkeypatch.setattr(credentials_module.facebook_oauth, "CALLBACK_URL", "https://h/cb")
    monkeypatch.setattr(credentials_module.facebook_oauth, "CONFIG_ID", "cfg")
    res = client.get("/credentials/facebook/authorize")

    assert res.status_code == 200
    assert "state=" in res.json()["url"]
    assert "facebook_oauth_state" in res.cookies


def test_facebook_callback_success_saves_credential_and_redirects(client, monkeypatch):
    saved = {}

    async def fake_get_user_auth_page_token(code):
        assert code == "meta-code-123"
        return "page-1", "Minha Página", "page-access-token", "fb-user-1"

    def fake_upsert(table, user_id, data, profile_id=None):
        saved["table"] = table
        saved["user_id"] = user_id
        saved["data"] = data
        return {**data, "id": 1}

    monkeypatch.setattr(
        credentials_module.facebook_oauth,
        "get_user_auth_page_token",
        fake_get_user_auth_page_token,
    )
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    # simula o cookie assinado que /authorize teria gravado
    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("facebook_oauth_state", cookie_value)

    res = client.get(
        "/credentials/facebook/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "facebook=success" in res.headers["location"]
    assert saved["table"] == "facebook_credentials"
    assert saved["user_id"] == 42
    assert saved["data"]["page_id"] == "page-1"
    assert saved["data"]["page_name"] == "Minha Página"
    assert saved["data"]["fb_user_id"] == "fb-user-1"
    assert saved["data"]["status"] is True
    # token nunca é gravado em texto puro
    assert saved["data"]["page_access_token"] != "page-access-token"


def test_facebook_callback_saves_without_fb_user_id_when_me_lookup_failed(client, monkeypatch):
    saved = {}

    async def fake_get_user_auth_page_token(code):
        return "page-1", "Minha Página", "page-access-token", None

    def fake_upsert(table, user_id, data, profile_id=None):
        saved.update(data)
        return {**data, "id": 1}

    monkeypatch.setattr(
        credentials_module.facebook_oauth,
        "get_user_auth_page_token",
        fake_get_user_auth_page_token,
    )
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("facebook_oauth_state", cookie_value)

    res = client.get(
        "/credentials/facebook/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "facebook=success" in res.headers["location"]
    assert saved["fb_user_id"] is None


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (None, httpx.TimeoutException("timeout secret-token")),
        (None, httpx.ConnectError("connect secret-token")),
        (type("BadJson", (), {"status_code": 200, "json": lambda self: (_ for _ in ()).throw(ValueError("bad secret-token"))})(), None),
        (type("MissingId", (), {"status_code": 200, "json": lambda self: {}})(), None),
    ],
)
def test_facebook_get_fb_user_id_is_best_effort_and_keeps_token_out_of_logs(
    monkeypatch, caplog, response, error
):
    calls = []

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if error:
                raise error
            return response

    monkeypatch.setattr(facebook_oauth.httpx, "AsyncClient", FakeClient)
    caplog.set_level(logging.WARNING)

    assert asyncio.run(facebook_oauth.get_fb_user_id("secret-token")) is None

    assert calls
    url, kwargs = calls[0]
    assert "secret-token" not in url
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["params"] == {"fields": "id"}
    assert "secret-token" not in caplog.text


def test_facebook_callback_error_from_meta_redirects_without_saving(client, monkeypatch):
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/facebook/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "facebook=error" in res.headers["location"]
    assert upsert_called is False


def test_facebook_callback_oauth_failure_redirects_without_saving(client, monkeypatch):
    async def fake_get_user_auth_page_token(code):
        raise credentials_module.facebook_oauth.FacebookOAuthError("no pages found")

    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(
        credentials_module.facebook_oauth,
        "get_user_auth_page_token",
        fake_get_user_auth_page_token,
    )
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("facebook_oauth_state", cookie_value)

    res = client.get(
        "/credentials/facebook/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "facebook=error" in res.headers["location"]
    assert "oauth_failed" in res.headers["location"]
    assert upsert_called is False


def test_facebook_callback_missing_state_redirects_without_saving(client, monkeypatch):
    """Sem cookie de state (ex.: callback acessado direto) — mesmo com
    `code` válido, não pode trocar por token (CSRF do account-linking)."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/facebook/callback",
        params={"code": "meta-code-123"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "facebook=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_facebook_callback_state_mismatch_redirects_without_saving(client, monkeypatch):
    """Cookie presente mas `state` da query não bate com o do
    /authorize — cenário de account-linking CSRF."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    _, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("facebook_oauth_state", cookie_value)

    res = client.get(
        "/credentials/facebook/callback",
        params={"code": "meta-code-123", "state": "attacker-controlled-state"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "facebook=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_facebook_authorize_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get("/credentials/facebook/authorize")
    assert res.status_code == 401


def test_facebook_callback_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get(
        "/credentials/facebook/callback", params={"code": "x"}
    )
    assert res.status_code == 401

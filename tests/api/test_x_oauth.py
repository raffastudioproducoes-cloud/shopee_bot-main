"""
Testes do fluxo OAuth 2.0 + PKCE do X (api/routers/credentials.py).

App único da plataforma (migração 2026-09-28 — X_CLIENT_ID/SECRET via
env, não mais por usuário): mesma estrutura de
tests/api/test_threads_oauth.py, sem precisar mockar credencial salva
antes do authorize/callback.
"""

import asyncio
import base64

import httpx
import pytest
from fastapi.testclient import TestClient

from api import x_oauth
from api.main import app
from api.routers import credentials as credentials_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


def test_x_authorize_returns_pkce_url_and_sets_state_cookie(client, monkeypatch):
    monkeypatch.setattr(credentials_module.x_oauth, "CLIENT_ID", "client-id-123")

    res = client.get("/credentials/x/authorize")

    assert res.status_code == 200
    url = res.json()["url"]
    assert "client_id=client-id-123" in url
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert "x_oauth_state" in res.cookies


def test_x_callback_success_saves_tokens_and_redirects(client, monkeypatch):
    saved = {}

    async def fake_exchange(code, code_verifier):
        assert code == "x-code-123"
        assert code_verifier == "verifier-abc"
        return {
            "access_token": "user-access-tok",
            "refresh_token": "user-refresh-tok",
            "expires_in": 7200,
        }

    monkeypatch.setattr(
        credentials_module.x_oauth, "exchange_code_for_token", fake_exchange
    )

    def fake_upsert(table, user_id, data):
        saved["table"] = table
        saved["user_id"] = user_id
        saved["data"] = data
        return {**data, "id": 1}

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    # simula o cookie assinado que /authorize teria gravado
    state, cookie_value = credentials_module._sign_oauth_state(
        42, {"code_verifier": "verifier-abc"}
    )
    client.cookies.set("x_oauth_state", cookie_value)

    res = client.get(
        "/credentials/x/callback",
        params={"code": "x-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "x=success" in res.headers["location"]
    assert saved["table"] == "x_credentials"
    assert saved["user_id"] == 42
    assert saved["data"]["status"] is True
    # token nunca é gravado em texto puro
    assert saved["data"]["user_access_token"] != "user-access-tok"


def test_x_callback_error_from_x_redirects_without_saving(client, monkeypatch):
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/x/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "x=error" in res.headers["location"]
    assert upsert_called is False


def test_x_callback_invalid_state_redirects_without_saving(client, monkeypatch):
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/x/callback",
        params={"code": "some-code", "state": "wrong-state"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "x=error" in res.headers["location"]
    assert upsert_called is False


def test_exchange_code_for_token_sends_basic_auth_header(monkeypatch):
    """X exige HTTP Basic Auth (client_id:client_secret) no POST de
    /2/oauth2/token pra confidential clients — só client_id/secret no
    body (suficiente pra TikTok/Meta) resulta em 401 "unauthorized_client
    / Missing valid authorization header". Regressão dessa checagem."""
    monkeypatch.setattr(x_oauth, "CLIENT_ID", "cid-123")
    monkeypatch.setattr(x_oauth, "CLIENT_SECRET", "csecret-456")

    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"access_token": "tok"}

    async def fake_post(self, url, headers=None, data=None):
        captured["headers"] = headers
        captured["data"] = data
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = asyncio.run(x_oauth.exchange_code_for_token("the-code", "the-verifier"))

    expected_auth = "Basic " + base64.b64encode(b"cid-123:csecret-456").decode()
    assert captured["headers"]["Authorization"] == expected_auth
    assert result == {"access_token": "tok"}
    # client_id NÃO pode ir no body quando o Basic Auth já é enviado —
    # RFC 6749 §3.2.1: confidential client não deve autenticar por mais
    # de um método na mesma requisição. Duplicar client_id no form body
    # junto do header Basic é o que o X rejeitava com 401
    # unauthorized_client / "Missing valid authorization header".
    assert "client_id" not in captured["data"]


def test_refresh_access_token_sends_basic_auth_header_without_client_id_in_body(
    monkeypatch,
):
    """Mesma checagem de test_exchange_code_for_token_sends_basic_auth_header,
    pra refresh_access_token: client_id não pode duplicar no body quando
    o Basic Auth já autentica o client."""
    monkeypatch.setattr(x_oauth, "CLIENT_ID", "cid-123")
    monkeypatch.setattr(x_oauth, "CLIENT_SECRET", "csecret-456")

    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"access_token": "tok"}

    async def fake_post(self, url, headers=None, data=None):
        captured["headers"] = headers
        captured["data"] = data
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = asyncio.run(x_oauth.refresh_access_token("the-refresh-token"))

    expected_auth = "Basic " + base64.b64encode(b"cid-123:csecret-456").decode()
    assert captured["headers"]["Authorization"] == expected_auth
    assert result == {"access_token": "tok"}
    assert "client_id" not in captured["data"]


def test_exchange_code_for_token_strips_whitespace_from_env_credentials(monkeypatch):
    """X_CLIENT_ID/X_CLIENT_SECRET lidos de env var no Render podem vir
    com espaço/newline colado (erro comum ao colar no dashboard). Isso
    vaza pro base64 do Basic Auth e produz um header presente mas
    garbled -> 401 unauthorized_client. Regressão do .strip() defensivo
    aplicado na leitura do env var em x_oauth.py."""
    monkeypatch.setattr(x_oauth, "CLIENT_ID", "cid-123\n")
    monkeypatch.setattr(x_oauth, "CLIENT_SECRET", " csecret-456 ")

    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"access_token": "tok"}

    async def fake_post(self, url, headers=None, data=None):
        captured["headers"] = headers
        captured["data"] = data
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    asyncio.run(x_oauth.exchange_code_for_token("the-code", "the-verifier"))

    expected_auth = "Basic " + base64.b64encode(b"cid-123:csecret-456").decode()
    assert captured["headers"]["Authorization"] == expected_auth


def test_x_authorize_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get("/credentials/x/authorize")
    assert res.status_code == 401


def test_x_callback_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get(
        "/credentials/x/callback", params={"code": "x"}
    )
    assert res.status_code == 401

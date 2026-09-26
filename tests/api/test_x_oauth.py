"""
Testes do fluxo OAuth 2.0 + PKCE do X (api/routers/credentials.py).

Mocka a troca de code por token (api/x_oauth.py) e o upsert de
credencial — cobre o caminho feliz de authorize/callback, mesma
estrutura de tests/api/test_threads_oauth.py.
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


class _FakeResult:
    def __init__(self, data):
        self.data = data


def _fake_supabase_row(data):
    """Monta um stand-in pra `supabase.table(...).select(...).eq(...)
    .maybe_single().execute()` retornando `data` fixo."""

    class _Chain:
        def select(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            return _FakeResult(data)

    class _Table:
        def table(self, *a, **kw):
            return _Chain()

    return _Table()


def test_x_authorize_returns_pkce_url_and_sets_state_cookie(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module,
        "supabase",
        _fake_supabase_row({"app_id": "client-id-123"}),
    )

    res = client.get("/credentials/x/authorize")

    assert res.status_code == 200
    url = res.json()["url"]
    assert "client_id=client-id-123" in url
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert "x_oauth_state" in res.cookies


def test_x_authorize_without_saved_app_credential_fails(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module, "supabase", _fake_supabase_row(None)
    )
    res = client.get("/credentials/x/authorize")
    assert res.status_code == 400


def test_x_callback_success_saves_tokens_and_redirects(client, monkeypatch):
    saved = {}

    monkeypatch.setattr(
        credentials_module,
        "supabase",
        _fake_supabase_row({"app_id": "client-id-123", "secret": "enc-secret"}),
    )
    monkeypatch.setattr(credentials_module, "decrypt", lambda v: "plain-secret")

    async def fake_exchange(client_id, client_secret, code, code_verifier):
        assert client_id == "client-id-123"
        assert client_secret == "plain-secret"
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

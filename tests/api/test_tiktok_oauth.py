"""
Testes do OAuth do TikTok (api/routers/credentials.py).

Mesmo espírito de tests/api/test_threads_oauth.py: mocka a troca de code
por token (api/tiktok_oauth.py) e o upsert de credencial, sem bater na
API de verdade nem precisar de um Supabase real. Roda com
`pytest --confcutdir=tests/api tests/api` (ver tests/api/conftest.py).

Diferença do Threads: o Client Key/Secret do TikTok é por usuário (não
um app global via env), então authorize/callback primeiro leem a
credencial já salva (`_get_tiktok_credentials_row`, mockada aqui em vez
do Supabase de verdade).

Cobre também a validação do `state` (CSRF do account-linking, ver HIGH
de api/routers/credentials.py): authorize seta o cookie, callback com
state ausente/errado falha antes de trocar code por token.
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


def test_tiktok_authorize_without_saved_client_key_fails_clearly(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module, "_get_tiktok_credentials_row", lambda user_id: None
    )

    res = client.get("/credentials/tiktok/authorize")

    assert res.status_code == 400


def test_tiktok_authorize_returns_url_with_saved_client_key(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module,
        "_get_tiktok_credentials_row",
        lambda user_id: {"app_id": "client-key-123", "secret": "enc-secret"},
    )

    res = client.get("/credentials/tiktok/authorize")

    assert res.status_code == 200
    assert "client-key-123" in res.json()["url"]
    assert "state=" in res.json()["url"]
    assert "tiktok_oauth_state" in res.cookies


def test_tiktok_callback_success_saves_credential_and_redirects(client, monkeypatch):
    saved = {}

    monkeypatch.setattr(
        credentials_module,
        "_get_tiktok_credentials_row",
        lambda user_id: {"app_id": "client-key-123", "secret": "enc-secret"},
    )
    monkeypatch.setattr(credentials_module, "decrypt", lambda v: "plain-secret")

    async def fake_get_user_auth_id_token(client_key, client_secret, code):
        assert client_key == "client-key-123"
        assert client_secret == "plain-secret"
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


def test_tiktok_callback_without_saved_client_credentials_fails_clearly(client, monkeypatch):
    monkeypatch.setattr(
        credentials_module, "_get_tiktok_credentials_row", lambda user_id: None
    )

    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("tiktok_oauth_state", cookie_value)

    res = client.get(
        "/credentials/tiktok/callback",
        params={"code": "tiktok-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "tiktok=error" in res.headers["location"]
    assert "missing_client_credentials" in res.headers["location"]


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

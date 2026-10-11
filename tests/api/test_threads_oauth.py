"""
Testes do fluxo OAuth do Threads (api/routers/credentials.py).

Mocka a troca de code por token (api/threads_oauth.py) e o upsert de
credencial — cobre o caminho feliz de authorize/callback, o caso de
erro vindo do Meta (?error=) e a validação do `state` (CSRF do
account-linking), mesma estrutura de tests/api/test_x_oauth.py.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import credentials as credentials_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


def test_threads_authorize_returns_url_and_sets_state_cookie(client, monkeypatch):
    monkeypatch.setattr(credentials_module.threads_oauth, "APP_ID", "app")
    monkeypatch.setattr(credentials_module.threads_oauth, "SECRET", "sec")
    monkeypatch.setattr(credentials_module.threads_oauth, "CALLBACK_URL", "https://h/cb")
    res = client.get("/credentials/threads/authorize")

    assert res.status_code == 200
    assert "state=" in res.json()["url"]
    assert "threads_oauth_state" in res.cookies


def test_threads_callback_success_saves_credential_and_redirects(client, monkeypatch):
    saved = {}

    async def fake_get_user_auth_id_token(code):
        assert code == "meta-code-123"
        return "threads-user-1", "long-lived-token"

    def fake_upsert(table, user_id, data, profile_id=None):
        saved["table"] = table
        saved["user_id"] = user_id
        saved["data"] = data
        return {**data, "id": 1}

    monkeypatch.setattr(
        credentials_module.threads_oauth,
        "get_user_auth_id_token",
        fake_get_user_auth_id_token,
    )
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    # simula o cookie assinado que /authorize teria gravado
    state, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("threads_oauth_state", cookie_value)

    res = client.get(
        "/credentials/threads/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "threads=success" in res.headers["location"]
    assert saved["table"] == "threads_credentials"
    assert saved["user_id"] == 42
    assert saved["data"]["t_user_id"] == "threads-user-1"
    assert saved["data"]["status"] is True
    # token nunca é gravado em texto puro
    assert saved["data"]["access_token"] != "long-lived-token"


def test_threads_callback_error_from_meta_redirects_without_saving(client, monkeypatch):
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/threads/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "threads=error" in res.headers["location"]
    assert upsert_called is False


def test_threads_callback_missing_state_redirects_without_saving(client, monkeypatch):
    """Sem cookie de state (ex.: callback acessado direto, sem passar
    pelo /authorize) — mesmo com um `code` válido, não pode trocar por
    token: seria o cenário de CSRF/account-linking descrito no HIGH."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    res = client.get(
        "/credentials/threads/callback",
        params={"code": "meta-code-123"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "threads=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_threads_callback_state_mismatch_redirects_without_saving(client, monkeypatch):
    """Cookie presente mas `state` da query não bate — ex.: atacante
    reusa o próprio link de callback (com o code dele) contra a sessão
    da vítima, que tem seu PRÓPRIO cookie/state do /authorize dela."""
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    _, cookie_value = credentials_module._sign_oauth_state(42)
    client.cookies.set("threads_oauth_state", cookie_value)

    res = client.get(
        "/credentials/threads/callback",
        params={"code": "meta-code-123", "state": "attacker-controlled-state"},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "threads=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_threads_callback_rejects_oauth_started_in_another_profile(client, monkeypatch):
    """A conta social deve ficar no perfil que iniciou o OAuth.

    Trocar de perfil em outra aba antes do callback não pode fazer a
    autorização gravar no perfil recém-ativo.
    """
    upsert_called = False

    def fake_upsert(*args, **kwargs):
        nonlocal upsert_called
        upsert_called = True

    app.dependency_overrides[get_current_profile_id] = lambda: "profile-b"
    monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)

    state, cookie_value = credentials_module._sign_oauth_state(
        42, profile_id="profile-a"
    )
    client.cookies.set("threads_oauth_state", cookie_value)

    res = client.get(
        "/credentials/threads/callback",
        params={"code": "meta-code-123", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "threads=error" in res.headers["location"]
    assert "invalid_state" in res.headers["location"]
    assert upsert_called is False


def test_threads_authorize_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get("/credentials/threads/authorize")
    assert res.status_code == 401


def test_threads_callback_requires_auth():
    app.dependency_overrides.clear()
    res = TestClient(app).get(
        "/credentials/threads/callback", params={"code": "x"}
    )
    assert res.status_code == 401

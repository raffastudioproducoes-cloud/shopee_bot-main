"""Teste de conexão (X, Instagram, TikTok): valida o token do USUÁRIO, não a
credencial do app. Respostas HTTP dos provedores mockadas; nenhuma chamada real.
"""
import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api import facebook_oauth, instagram_oauth, threads_oauth, tiktok_oauth, x_oauth  # noqa: F401
from api.crypto import decrypt
from api.main import app
from api.routers import credentials as cred
from api.routers.auth import get_current_user_id
from shopee_bot.apis import instagram as igapi
from shopee_bot.apis import tiktok as ttapi
from shopee_bot.apis import x as xapi
from shopee_bot.utils import ConnectionTestError

USER_TOKEN = "USER-ACCESS-TOKEN-xyz"
REFRESH = "USER-REFRESH-TOKEN-abc"
NEW_TOKEN = "NEW-ACCESS-TOKEN-777"
NEW_REFRESH = "NEW-REFRESH-TOKEN-888"


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body if body is not None else {}
        self.text = str(self._body)

    def json(self):
        return self._body


class FakeRequests:
    """Substitui o módulo requests do apis/*.py; roteia por URL."""

    exceptions = SimpleNamespace(RequestException=OSError)

    def __init__(self, routes):
        self.routes = routes  # lista de (metodo, trecho_da_url, [respostas])
        self.calls = []

    def _do(self, method, url, **kw):
        self.calls.append((method, url, kw))
        for m, frag, queue in self.routes:
            if m == method and frag in url:
                return queue.pop(0) if len(queue) > 1 else queue[0]
        raise AssertionError(f"chamada inesperada: {method} {url}")

    def get(self, url, **kw):
        return self._do("GET", url, **kw)

    def post(self, url, **kw):
        return self._do("POST", url, **kw)


def _install(monkeypatch, module, routes):
    fake = FakeRequests(routes)
    monkeypatch.setattr(module, "requests", fake)
    return fake


# -- X ------------------------------------------------------------------------
ME_OK = Resp(200, {"data": {"id": "1", "username": "u"}})


def test_x_valid_user_token_uses_users_me_with_user_bearer(monkeypatch):
    fake = _install(monkeypatch, xapi, [("GET", "/2/users/me", [ME_OK])])
    user, refreshed = xapi.validate_user_token("cid", "sec", USER_TOKEN, REFRESH)
    assert user["id"] == "1" and refreshed is None
    assert [c[0] for c in fake.calls] == ["GET"]  # sem client_credentials
    assert fake.calls[0][2]["headers"]["Authorization"] == f"Bearer {USER_TOKEN}"


def test_x_401_refreshes_and_retries(monkeypatch):
    fake = _install(monkeypatch, xapi, [
        ("GET", "/2/users/me", [Resp(401), ME_OK]),
        ("POST", "/oauth2/token", [Resp(200, {"access_token": NEW_TOKEN, "refresh_token": NEW_REFRESH, "expires_in": 7200})]),
    ])
    user, refreshed = xapi.validate_user_token("cid", "sec", USER_TOKEN, REFRESH)
    assert refreshed["access_token"] == NEW_TOKEN
    gets = [c for c in fake.calls if c[0] == "GET"]
    assert gets[1][2]["headers"]["Authorization"] == f"Bearer {NEW_TOKEN}"
    assert fake.calls[1][2]["data"]["grant_type"] == "refresh_token"


def test_x_401_without_refresh_token_asks_reconnect(monkeypatch):
    _install(monkeypatch, xapi, [("GET", "/2/users/me", [Resp(401)])])
    with pytest.raises(ConnectionTestError) as e:
        xapi.validate_user_token("cid", "sec", USER_TOKEN, None)
    assert "reconecte" in str(e.value) and USER_TOKEN not in str(e.value)


def test_x_refresh_failure_does_not_leak_tokens(monkeypatch):
    _install(monkeypatch, xapi, [
        ("GET", "/2/users/me", [Resp(401)]),
        ("POST", "/oauth2/token", [Resp(400, {"error": "invalid_request", "echo": REFRESH})]),
    ])
    with pytest.raises(ConnectionTestError) as e:
        xapi.validate_user_token("cid", "sec", USER_TOKEN, REFRESH)
    assert "reconecte" in str(e.value)
    assert REFRESH not in str(e.value) and USER_TOKEN not in str(e.value)


def test_x_still_401_after_refresh_keeps_new_tokens_on_error(monkeypatch):
    _install(monkeypatch, xapi, [
        ("GET", "/2/users/me", [Resp(401)]),
        ("POST", "/oauth2/token", [Resp(200, {"access_token": NEW_TOKEN, "refresh_token": NEW_REFRESH})]),
    ])
    with pytest.raises(ConnectionTestError) as e:
        xapi.validate_user_token("cid", "sec", USER_TOKEN, REFRESH)
    assert e.value.refreshed["refresh_token"] == NEW_REFRESH  # rotacao nao se perde


def test_x_403_mentions_read_and_write(monkeypatch):
    _install(monkeypatch, xapi, [("GET", "/2/users/me", [Resp(403)])])
    with pytest.raises(ConnectionTestError) as e:
        xapi.validate_user_token("cid", "sec", USER_TOKEN, REFRESH)
    assert "Read and write" in str(e.value)


# -- Instagram ----------------------------------------------------------------
def test_instagram_valid_user_token_uses_user_token_and_v19(monkeypatch):
    fake = _install(monkeypatch, igapi, [
        ("GET", "/v19.0/me", [Resp(200, {"id": "10"})]),
        ("GET", "/v19.0/178", [Resp(200, {"id": "178", "username": "ig"})]),
    ])
    result = igapi.validate_user_token(USER_TOKEN, "178")
    assert result["ig_user_id"] == "178"
    assert all(c[2]["params"]["access_token"] == USER_TOKEN for c in fake.calls)
    assert not any("oauth/access_token" in c[1] for c in fake.calls)  # sem app token


def test_instagram_expired_token_asks_reconnect_without_leak(monkeypatch):
    err = {"error": {"message": f"Error validating access token {USER_TOKEN}", "code": 190}}
    _install(monkeypatch, igapi, [("GET", "/v19.0/me", [Resp(400, err)])])
    with pytest.raises(ConnectionTestError) as e:
        igapi.validate_user_token(USER_TOKEN, "178")
    assert "expirado" in str(e.value) and "reconecte" in str(e.value)
    assert USER_TOKEN not in str(e.value)


def test_instagram_without_saved_id_and_no_business_page(monkeypatch):
    _install(monkeypatch, igapi, [
        ("GET", "/v19.0/me/accounts", [Resp(200, {"data": [{"id": "p1"}]})]),
        ("GET", "/v19.0/me", [Resp(200, {"id": "10"})]),
    ])
    with pytest.raises(ConnectionTestError) as e:
        igapi.validate_user_token(USER_TOKEN, None)
    assert "Nenhuma Página" in str(e.value)


# -- TikTok -------------------------------------------------------------------
TT_OK = Resp(200, {"data": {"user": {"open_id": "o1", "display_name": "n"}}, "error": {"code": "ok"}})


def _tt_err(code, status=401):
    return Resp(status, {"data": {}, "error": {"code": code, "message": f"x {USER_TOKEN}"}})


def test_tiktok_valid(monkeypatch):
    fake = _install(monkeypatch, ttapi, [("GET", "/user/info/", [TT_OK])])
    user, refreshed = ttapi.validate_user_token("ck", "cs", USER_TOKEN, REFRESH)
    assert user["open_id"] == "o1" and refreshed is None
    assert fake.calls[0][2]["headers"]["Authorization"] == f"Bearer {USER_TOKEN}"


def test_tiktok_invalid_token_refreshes_and_retries(monkeypatch):
    fake = _install(monkeypatch, ttapi, [
        ("GET", "/user/info/", [_tt_err("access_token_invalid"), TT_OK]),
        ("POST", "/oauth/token/", [Resp(200, {"access_token": NEW_TOKEN, "refresh_token": NEW_REFRESH})]),
    ])
    user, refreshed = ttapi.validate_user_token("ck", "cs", USER_TOKEN, REFRESH)
    assert refreshed["access_token"] == NEW_TOKEN
    gets = [c for c in fake.calls if c[0] == "GET"]
    assert gets[1][2]["headers"]["Authorization"] == f"Bearer {NEW_TOKEN}"


def test_tiktok_invalid_token_without_refresh(monkeypatch):
    _install(monkeypatch, ttapi, [("GET", "/user/info/", [_tt_err("access_token_invalid")])])
    with pytest.raises(ConnectionTestError) as e:
        ttapi.validate_user_token("ck", "cs", USER_TOKEN, None)
    assert "reconecte" in str(e.value) and USER_TOKEN not in str(e.value)


def test_tiktok_scope_not_authorized(monkeypatch):
    _install(monkeypatch, ttapi, [("GET", "/user/info/", [_tt_err("scope_not_authorized", 403)])])
    with pytest.raises(ConnectionTestError) as e:
        ttapi.validate_user_token("ck", "cs", USER_TOKEN, REFRESH)
    assert "user.info.basic" in str(e.value) and USER_TOKEN not in str(e.value)


# -- API: persistencia dos tokens renovados + payload -------------------------
@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "users": [{"id": 42, "access": "USER"}],
        "x_credentials": [{
            "id": 1, "user_id": 42, "user_access_token": cred.encrypt(USER_TOKEN),
            "user_refresh_token": cred.encrypt(REFRESH), "status": True,
        }],
        "tiktok_credentials": [{
            "id": 2, "user_id": 42, "user_access_token": cred.encrypt(USER_TOKEN),
            "refresh_token": cred.encrypt(REFRESH), "status": True,
        }],
        "instagram_credentials": [{
            "id": 3, "user_id": 42, "user_access_token": cred.encrypt(USER_TOKEN),
            "ig_user_id": "178", "status": True,
        }],
        "credential_checks": [],
    })
    monkeypatch.setattr(cred, "supabase", database)
    monkeypatch.setattr(cred, "log_action", lambda *a, **k: None)
    cred._test_attempts.clear()
    # _OAUTH_GLOBAL_APP e montado no import (env pode estar vazio no CI)
    monkeypatch.setattr(cred, "_OAUTH_GLOBAL_APP", {
        "x": ("cid", "csec"), "tiktok": ("ck", "cs"), "instagram": ("aid", "asec"),
    })
    return database


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_payload_carries_refresh_token_and_ig_id(db):
    px = cred._test_payload("x", 42)
    assert px["user_access_token"] == USER_TOKEN and px["refresh_token"] == REFRESH
    assert cred._test_payload("tiktok", 42)["refresh_token"] == REFRESH
    assert cred._test_payload("instagram", 42)["ig_user_id"] == "178"


@pytest.mark.parametrize("network,table,refresh_col", [
    ("x", "x_credentials", "user_refresh_token"),
    ("tiktok", "tiktok_credentials", "refresh_token"),
])
def test_manual_test_persists_refreshed_tokens(db, client, monkeypatch, network, table, refresh_col):
    async def bridge(net, payload):
        return {"state": "ok", "message": "Conectado",
                "refreshed_tokens": {"access_token": NEW_TOKEN, "refresh_token": NEW_REFRESH, "expires_in": 7200}}

    monkeypatch.setattr(cred, "validate_network_credential", bridge)
    res = client.post(f"/credentials/{network}/test")
    assert res.status_code == 200
    row = db.tables[table][0]
    assert decrypt(row["user_access_token"]) == NEW_TOKEN
    assert decrypt(row[refresh_col]) == NEW_REFRESH
    assert NEW_TOKEN not in res.text and NEW_REFRESH not in res.text


def test_failed_test_still_persists_rotated_tokens(db, client, monkeypatch):
    async def bridge(net, payload):
        return {"state": "error", "message": "x",
                "refreshed_tokens": {"access_token": NEW_TOKEN, "refresh_token": NEW_REFRESH}}

    monkeypatch.setattr(cred, "validate_network_credential", bridge)
    client.post("/credentials/x/test")
    assert decrypt(db.tables["x_credentials"][0]["user_refresh_token"]) == NEW_REFRESH


# -- Configuracao do servidor ausente -> 503 ----------------------------------
_FULL_CONFIG = [
    (threads_oauth, "APP_ID"), (threads_oauth, "SECRET"), (threads_oauth, "CALLBACK_URL"),
    (x_oauth, "CLIENT_ID"), (x_oauth, "CLIENT_SECRET"), (x_oauth, "CALLBACK_URL"),
    (instagram_oauth, "APP_ID"), (instagram_oauth, "SECRET"),
    (instagram_oauth, "CALLBACK_URL"), (instagram_oauth, "CONFIG_ID"),
    (facebook_oauth, "CALLBACK_URL"), (facebook_oauth, "CONFIG_ID"),
]


@pytest.mark.parametrize("network,module,attr", [
    ("threads", threads_oauth, "CALLBACK_URL"),
    ("threads", threads_oauth, "APP_ID"),
    ("x", x_oauth, "CALLBACK_URL"),
    ("x", x_oauth, "CLIENT_ID"),
    ("facebook", facebook_oauth, "CALLBACK_URL"),
    ("facebook", facebook_oauth, "CONFIG_ID"),
    ("instagram", instagram_oauth, "CALLBACK_URL"),
    ("instagram", instagram_oauth, "APP_ID"),
])
def test_authorize_without_server_config_returns_503(client, monkeypatch, caplog, network, module, attr):
    for mod, a in _FULL_CONFIG:
        monkeypatch.setattr(mod, a, "valor-de-teste")
    monkeypatch.setattr(module, attr, None)
    monkeypatch.setattr(cred, "log_action", lambda *a, **k: None)
    with caplog.at_level(logging.ERROR):
        res = client.get(f"/credentials/{network}/authorize")
    assert res.status_code == 503
    assert "configuração do servidor incompleta" in res.json()["detail"]
    assert "None" not in res.text
    assert any("OAuth" in r.message for r in caplog.records)

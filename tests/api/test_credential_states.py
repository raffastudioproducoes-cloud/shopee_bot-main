"""
Luz + selo coerentes por estado da credencial (conectado, nunca testado,
erro, teste antigo, token expirado) e teste zerado ao salvar/reconectar.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from api import database as database_module
from api.routers import credentials as cred


def _now_iso(**delta):
    return (datetime.now(timezone.utc) - timedelta(**delta)).isoformat()


def test_disconnected_is_red():
    assert cred._connection_state(False, {"state": "ok"})[:2] == ("red", "disconnected")


def test_saved_never_tested_explains_red():
    light, state, text = cred._connection_state(True, None)
    assert (light, state) == ("red", "untested")
    assert "nunca testada" in text


def test_recent_ok_is_green():
    assert cred._connection_state(True, {"state": "ok", "checked_at": _now_iso(hours=1)})[:2] == ("green", "ok")


def test_old_ok_check_expires_to_yellow():
    light, state, _ = cred._connection_state(True, {"state": "ok", "checked_at": _now_iso(days=8)})
    assert (light, state) == ("yellow", "stale")


def test_error_shows_short_sanitized_reason():
    msg = "401 invalid token access_token=SEGREDO123 " + "x" * 300
    light, state, text = cred._connection_state(True, {"state": "error", "message": msg})
    assert (light, state) == ("yellow", "error")
    assert text.startswith("Erro: ")
    assert "SEGREDO123" not in text
    assert len(text) <= 130


def test_x_expired_token_without_refresh_asks_reconnect():
    row = {"user_access_token": "enc", "token_expires_at": _now_iso(hours=1), "user_refresh_token": None}
    status = cred._status_only(row, {"state": "ok", "checked_at": _now_iso(minutes=5)},
                               token_field="user_access_token", network="x")
    assert status["connected"] is True
    assert (status["light"], status["state"]) == ("yellow", "expired")
    assert "reconecte" in status["status_text"]


def test_x_expired_token_with_refresh_is_not_expired():
    row = {"user_access_token": "enc", "token_expires_at": _now_iso(hours=1), "user_refresh_token": "r"}
    status = cred._status_only(row, None, token_field="user_access_token", network="x")
    assert status["state"] == "untested"


def test_upsert_resets_previous_check():
    fake = MagicMock()
    calls = []

    def table(name):
        q = MagicMock()
        for m in ("select", "eq", "maybe_single", "update", "insert", "delete"):
            getattr(q, m).return_value = q
        q.execute.return_value = MagicMock(data=[{"id": 1}])
        if name == "credential_checks":
            calls.append(q)
        return q

    fake.table.side_effect = table
    database_module_get = database_module.get_supabase
    database_module.get_supabase = lambda: fake
    try:
        cred._upsert_by_user("x_credentials", "u1", {"user_access_token": "enc"}, profile_id="p1")
    finally:
        database_module.get_supabase = database_module_get

    assert len(calls) == 1
    q = calls[0]
    q.delete.assert_called_once()
    q.eq.assert_any_call("network", "x")
    q.eq.assert_any_call("user_id", "u1")
    q.eq.assert_any_call("profile_id", "p1")


def test_test_endpoint_rate_limited(monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app
    from api.routers.auth import get_current_user_id

    cred._test_attempts.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "u-rate"
    monkeypatch.setattr(cred, "_test_payload", lambda network, user_id, profile_id=None: None)
    try:
        client = TestClient(app)
        codes = [client.post("/credentials/shopee/test").status_code for _ in range(cred._TEST_RATE_LIMIT_ATTEMPTS + 1)]
    finally:
        app.dependency_overrides.clear()
        cred._test_attempts.clear()
    assert codes[:-1] == [400] * cred._TEST_RATE_LIMIT_ATTEMPTS
    assert codes[-1] == 429

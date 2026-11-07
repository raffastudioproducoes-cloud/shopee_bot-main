"""Teste automático de IA global e credenciais sociais (nenhum provedor real)."""
import logging
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.crypto import decrypt, encrypt
from api.internal_client import InternalApiError
from api.main import app
from api.routers import credentials as cred, platform_ai as ai, users as users_module
from api.routers.auth import get_current_user_id
from apis import llm

SECRET = "chave-global-teste"


@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "users": [{"id": 7, "access": "ADMIN"}, {"id": 42, "access": "USER"}],
        "platform_ai_settings": [{"environment": "production", "active_provider": None}],
        "platform_ai_credentials": [],
        "ai_credentials": [], "shopee_credentials": [], "credential_checks": [],
    })
    for module in (cred, ai, users_module):
        monkeypatch.setattr(module, "supabase", database)
    monkeypatch.setattr(cred, "log_action", lambda *a, **k: None)
    monkeypatch.setattr(ai, "log_action", lambda *a, **k: None)
    cred._test_attempts.clear()
    return database


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 7
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def inline(monkeypatch):
    monkeypatch.setattr(ai, "_autotest_submit", lambda fn, *args: fn(*args))
    monkeypatch.setattr(cred, "_autotest_submit", lambda fn, *args: fn(*args))


@pytest.fixture
def deferred(monkeypatch):
    jobs = []
    monkeypatch.setattr(ai, "_autotest_submit", lambda fn, *args: jobs.append((fn, args)))
    return jobs


def _ai_row(db, provider="gemini"):
    return next((row for row in db.tables["platform_ai_credentials"] if row["provider"] == provider), None)


def _check(db, network):
    return next((row for row in db.tables["credential_checks"] if row["network"] == network), None)


def test_platform_ai_autotest_marks_testing_then_green(db, client, deferred, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    assert client.put("/admin/ai/gemini", json={"api_key": SECRET}).status_code == 200
    status = client.get("/admin/ai").json()["providers"]["gemini"]
    assert (status["state"], status["status_text"]) == ("testing", "Testando…")
    assert decrypt(_ai_row(db)["secret"]) == SECRET
    for fn, args in deferred:
        fn(*args)
    status = client.get("/admin/ai").json()["providers"]["gemini"]
    assert (status["state"], status["status_text"]) == ("ok", "Funcionando")
    assert status["checked_at"]


def test_platform_ai_provider_error_without_key_leak(db, client, inline, monkeypatch, caplog):
    def bad_key(*a, **k):
        raise llm.LLMError("invalid_key", "Chave inválida no provedor")
    monkeypatch.setattr(llm, "check_key", bad_key)
    with caplog.at_level(logging.DEBUG):
        response = client.put("/admin/ai/openai", json={"api_key": SECRET})
    status = client.get("/admin/ai").json()["providers"]["openai"]
    assert status["state"] == "error" and status["light"] == "yellow"
    assert "inválida" in status["status_text"]
    assert SECRET not in response.text + caplog.text + str(db.tables["platform_ai_credentials"])


def test_platform_ai_unexpected_exception_never_stuck(db, client, inline, monkeypatch, caplog):
    monkeypatch.setattr(llm, "check_key", lambda *a: (_ for _ in ()).throw(RuntimeError("no log " + SECRET)))
    with caplog.at_level(logging.DEBUG):
        client.put("/admin/ai/gemini", json={"api_key": SECRET})
    assert _ai_row(db)["check_state"] == "error"
    assert SECRET not in caplog.text and SECRET not in (_ai_row(db).get("check_message") or "")


def test_platform_ai_autotest_timeout(db, client, inline, monkeypatch):
    monkeypatch.setattr(cred, "AUTOTEST_TIMEOUT_SECONDS", 0.15)
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: time.sleep(2))
    started = time.monotonic()
    client.put("/admin/ai/gemini", json={"api_key": SECRET})
    assert time.monotonic() - started < 1.5
    assert _ai_row(db)["check_state"] == "error"


def test_platform_ai_old_worker_does_not_overwrite_new_key_test(db, client, deferred, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    client.put("/admin/ai/gemini", json={"api_key": "old"})
    time.sleep(0.01)
    client.put("/admin/ai/gemini", json={"api_key": "new"})
    first, second = deferred
    second[0](*second[1])
    assert _ai_row(db)["check_state"] == "ok"
    first[0](*first[1])
    assert _ai_row(db)["check_state"] == "ok"


def test_platform_ai_autotest_cannot_restore_disconnected_key(db, client, deferred, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    client.put("/admin/ai/gemini", json={"api_key": SECRET})
    client.delete("/admin/ai/gemini")
    for fn, args in deferred:
        fn(*args)
    assert _ai_row(db)["secret"] is None and _ai_row(db)["check_state"] is None


def test_platform_ai_save_survives_failed_autotest_dispatch(db, client, monkeypatch):
    monkeypatch.setattr(ai, "_autotest_submit", lambda *a: (_ for _ in ()).throw(RuntimeError("worker down")))
    response = client.put("/admin/ai/gemini", json={"api_key": SECRET})
    assert response.status_code == 200
    assert decrypt(_ai_row(db)["secret"]) == SECRET


def test_platform_ai_autotest_does_not_consume_manual_limit(db, client, deferred, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    for provider in ("gemini", "openai", "anthropic"):
        client.put(f"/admin/ai/{provider}", json={"api_key": SECRET})
    assert cred._test_attempts == {}
    assert client.post("/admin/ai/gemini/test").status_code == 200


def test_stuck_testing_expires_into_error():
    old = (datetime.now(timezone.utc) - cred.TESTING_MAX_AGE - timedelta(seconds=5)).isoformat()
    light, state, text = cred._connection_state(True, {"state": "testing", "message": "", "checked_at": old})
    assert (light, state) == ("yellow", "error") and "não terminou" in text


def test_shopee_autotests_still_use_bridge(db, client, monkeypatch):
    pending = []
    monkeypatch.setattr(cred, "_autotest_submit", lambda fn, *args: pending.append((fn, args)))
    async def valid(app_id, secret):
        return True
    async def bridge(network, payload):
        assert network == "shopee" and payload["secret"] == "seg-shopee"
        return {"state": "ok", "message": "Conta OK"}
    monkeypatch.setattr(cred, "validate_shopee_credential", valid)
    monkeypatch.setattr(cred, "validate_network_credential", bridge)
    assert client.put("/credentials/shopee", json={"app_id": "123", "secret": "seg-shopee"}).status_code == 200
    for fn, args in pending:
        fn(*args)
    assert client.get("/credentials").json()["shopee"]["state"] == "ok"


def test_shopee_bridge_down_becomes_safe_error(db, client, monkeypatch):
    pending = []
    monkeypatch.setattr(cred, "_autotest_submit", lambda fn, *args: pending.append((fn, args)))
    async def valid(app_id, secret):
        return True
    async def down(network, payload):
        raise InternalApiError("bridge fora")
    monkeypatch.setattr(cred, "validate_shopee_credential", valid)
    monkeypatch.setattr(cred, "validate_network_credential", down)
    client.put("/credentials/shopee", json={"app_id": "123", "secret": "seg-shopee"})
    for fn, args in pending:
        fn(*args)
    assert client.get("/credentials").json()["shopee"]["state"] == "error"


def test_latest_check_prefers_serial_id_when_timestamps_tie():
    latest = cred._latest_check([
        {"id": 9, "checked_at": "2026-10-11T12:00:00+00:00"},
        {"id": 10, "checked_at": "2026-10-11T12:00:00+00:00"},
    ])
    assert latest["id"] == 10


def test_social_account_checks_remain_scoped(db, client, profile_cookie):
    now = datetime.now(timezone.utc).isoformat()
    db.tables["shopee_credentials"].append({"id": 1, "user_id": 7, "status": True})
    db.tables["credential_checks"] = [
        {"id": 2, "user_id": 7, "network": "shopee", "state": "ok", "checked_at": now},
        {"id": 1, "user_id": 7, "network": "shopee", "state": "error", "checked_at": "2026-10-11T09:00:00+00:00"},
    ]
    client.cookies.update(profile_cookie("profile-a"))
    assert client.get("/credentials").json()["shopee"]["state"] == "ok"
    cred._save_check(7, "profile-b", "shopee", "error", "atual")
    assert len(db.tables["credential_checks"]) == 1


def test_user_cannot_override_social_credential(db, client):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    response = client.put("/admin/credentials/threads", json={"t_user_id": "1", "access_token": "token"})
    assert response.status_code == 403

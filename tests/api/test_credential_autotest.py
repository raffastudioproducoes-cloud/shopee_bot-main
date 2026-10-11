"""Teste automatico pos-salvar: salvar grava testing, o worker faz o teste
real e grava o resultado. Provedores/bridge mockados (nenhuma chamada real)."""
import logging
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.internal_client import InternalApiError
from api.main import app
from api.routers import credentials as cred
from api.routers.auth import get_current_user_id
from apis import llm

SECRET = "sk-test-SEGREDO-123"


@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "users": [{"id": 42, "access": "USER"}],
        "ai_credentials": [], "shopee_credentials": [], "credential_checks": [],
    })
    monkeypatch.setattr(cred, "supabase", database)
    monkeypatch.setattr(cred, "log_action", lambda *a, **k: None)
    cred._test_attempts.clear()
    return database


@pytest.fixture
def inline(monkeypatch):
    monkeypatch.setattr(cred, "_autotest_submit", lambda fn, *a: fn(*a))


@pytest.fixture
def deferred(monkeypatch):
    jobs = []
    monkeypatch.setattr(cred, "_autotest_submit", lambda fn, *a: jobs.append((fn, a)))
    return jobs


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    yield TestClient(app)
    app.dependency_overrides.clear()


def _check(db, network):
    return next((c for c in db.tables["credential_checks"] if c["network"] == network), None)


def _quota_error(*a, **k):
    raise llm.LLMError("quota", "Cota")


def test_ai_save_marks_testing_then_worker_sets_green(db, client, deferred, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)

    assert client.put("/credentials/ai/gemini", json={"api_key": SECRET}).status_code == 200
    shown = client.get("/credentials/ai").json()["providers"]["gemini"]
    assert (shown["state"], shown["status_text"]) == ("testing", "Testando…")

    for fn, args in deferred:
        fn(*args)
    shown = client.get("/credentials/ai").json()["providers"]["gemini"]
    assert (shown["light"], shown["state"], shown["status_text"]) == ("green", "ok", "Funcionando")
    assert shown["checked_at"]


def test_ai_provider_error_becomes_error_state_without_secret(db, client, inline, monkeypatch, caplog):
    def boom(*a, **k):
        raise llm.LLMError("invalid_key", "Chave invalida. Confira a chave de API.")
    monkeypatch.setattr(llm, "check_key", boom)

    with caplog.at_level(logging.DEBUG):
        res = client.put("/credentials/ai/openai", json={"api_key": SECRET})
    listed = client.get("/credentials/ai")

    shown = listed.json()["providers"]["openai"]
    assert (shown["light"], shown["state"]) == ("yellow", "error")
    assert "Chave invalida" in shown["status_text"]
    for text in (res.text, listed.text, caplog.text, str(db.tables["credential_checks"])):
        assert SECRET not in text


def test_unexpected_exception_never_leaves_testing(db, client, inline, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError("explodiu com " + SECRET)
    monkeypatch.setattr(llm, "check_key", boom)

    with caplog.at_level(logging.DEBUG):
        client.put("/credentials/ai/anthropic", json={"api_key": SECRET})

    check = _check(db, "ai_anthropic")
    assert check["state"] == "error" and SECRET not in str(check) and SECRET not in caplog.text


def test_slow_provider_times_out_and_does_not_hang(db, client, inline, monkeypatch):
    monkeypatch.setattr(cred, "AUTOTEST_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: time.sleep(2))

    started = time.monotonic()
    client.put("/credentials/ai/gemini", json={"api_key": SECRET})

    assert time.monotonic() - started < 1.5
    check = _check(db, "ai_gemini")
    assert check["state"] == "error" and "tempo limite" in check["message"]


def test_stuck_testing_expires_into_error():
    old = (datetime.now(timezone.utc) - cred.TESTING_MAX_AGE - timedelta(seconds=5)).isoformat()
    light, state, text = cred._connection_state(True, {"state": "testing", "message": "", "checked_at": old})
    assert (light, state) == ("yellow", "error") and "não terminou" in text


def test_older_worker_result_is_discarded_after_resave(db, client, deferred, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    client.put("/credentials/ai/gemini", json={"api_key": "chave-antiga"})
    time.sleep(0.01)
    client.put("/credentials/ai/gemini", json={"api_key": "chave-nova"})
    first, second = deferred

    second[0](*second[1])
    assert _check(db, "ai_gemini")["state"] == "ok"
    monkeypatch.setattr(llm, "check_key", _quota_error)
    first[0](*first[1])
    assert _check(db, "ai_gemini")["state"] == "ok"


def test_worker_skips_when_credential_was_disconnected(db, client, deferred, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    client.put("/credentials/ai/gemini", json={"api_key": SECRET})
    client.delete("/credentials/ai/gemini")
    for fn, args in deferred:
        fn(*args)
    assert _check(db, "ai_gemini") is None


def test_shopee_save_autotests_via_bridge(db, client, inline, monkeypatch):
    async def valid(app_id, secret):
        return True

    async def bridge(network, payload):
        assert network == "shopee" and payload["secret"] == "seg-shopee"
        return {"state": "ok", "message": "Conta de afiliado OK"}

    monkeypatch.setattr(cred, "validate_shopee_credential", valid)
    monkeypatch.setattr(cred, "validate_network_credential", bridge)

    assert client.put("/credentials/shopee", json={"app_id": "123", "secret": "seg-shopee"}).status_code == 200
    status = client.get("/credentials").json()["shopee"]
    assert (status["light"], status["state"]) == ("green", "ok")


def test_shopee_bridge_down_becomes_error(db, client, inline, monkeypatch):
    async def valid(app_id, secret):
        return True

    async def down(network, payload):
        raise InternalApiError("bridge fora")

    monkeypatch.setattr(cred, "validate_shopee_credential", valid)
    monkeypatch.setattr(cred, "validate_network_credential", down)

    client.put("/credentials/shopee", json={"app_id": "123", "secret": "seg-shopee"})
    status = client.get("/credentials").json()["shopee"]
    assert status["state"] == "error" and "bridge fora" not in status["status_text"]


def test_autotest_does_not_consume_manual_rate_limit(db, client, inline, monkeypatch):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    for provider in ("gemini", "openai", "anthropic") * 3:
        assert client.put("/credentials/ai/" + provider, json={"api_key": SECRET}).status_code == 200
    assert cred._test_attempts == {}
    assert client.post("/credentials/ai/gemini/test").status_code == 200


def test_ai_autotest_is_shared_by_account(db, client, deferred, monkeypatch, profile_cookie):
    monkeypatch.setattr(llm, "check_key", lambda *a, **k: None)
    client.cookies.update(profile_cookie("profile-a"))
    client.put("/credentials/ai/gemini", json={"api_key": SECRET})
    other = TestClient(app)
    other.cookies.update(profile_cookie("profile-b"))

    assert "profile_id" not in _check(db, "ai_gemini")
    assert other.get("/credentials/ai").json()["providers"]["gemini"]["state"] == "testing"
    for fn, args in deferred:
        fn(*args)
    assert other.get("/credentials/ai").json()["providers"]["gemini"]["state"] == "ok"
    assert client.get("/credentials/ai").json()["providers"]["gemini"]["state"] == "ok"


def test_save_still_succeeds_when_autotest_cannot_start(db, client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db fora")
    monkeypatch.setattr(cred, "_save_check", boom)
    assert client.put("/credentials/ai/gemini", json={"api_key": SECRET}).status_code == 200

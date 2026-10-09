"""Chave de IA por usuário/perfil: cifrada, escopada, sem chave global e sem
vazar o segredo em resposta/log. Provedores mockados (nenhuma chamada real)."""
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from api.crypto import decrypt, encrypt
from api.main import app
from api.routers import credentials as credentials_module
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from apis import llm

SECRET = "sk-test-SEGREDO-123"


@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "users": [{"id": 42, "access": "USER"}],
        "products": [{"id": 1, "user_id": 42, "name": "Fone", "commission": 10,
                      "price_min": 10, "price_max": 20, "commission_link": "https://s.shopee/x"}],
        "ai_credentials": [],
        "credential_checks": [],
    })
    monkeypatch.setattr(credentials_module, "supabase", database)
    monkeypatch.setattr(posts_module, "supabase", database)
    monkeypatch.setattr(credentials_module, "log_action", lambda *a, **k: None)
    credentials_module._test_attempts.clear()
    return database


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def provider_calls(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        if "googleapis" in url:
            body = {"candidates": [{"content": {"parts": [{"text": "pensando", "thought": True},
                                                          {"text": "Texto IA"}]}}]}
        elif "openai" in url:
            body = {"output": [{"type": "reasoning"},
                               {"type": "message", "content": [{"type": "output_text", "text": "Texto IA"}]}]}
        else:
            body = {"content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "Texto IA"}]}
        return httpx.Response(200, json=body)

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    return calls


def test_save_encrypts_and_never_returns_secret(db, client):
    res = client.put("/credentials/ai/gemini", json={"api_key": f"  {SECRET} "})

    assert res.status_code == 200 and SECRET not in res.text
    row = db.tables["ai_credentials"][0]
    assert row["secret"] != SECRET and decrypt(row["secret"]) == SECRET
    assert row["user_id"] == 42 and row["provider"] == "gemini" and row["status"] is True

    listed = client.get("/credentials/ai")
    assert listed.status_code == 200 and SECRET not in listed.text
    body = listed.json()
    assert body["active"] == "gemini"
    assert body["providers"]["gemini"]["connected"] is True
    assert body["providers"]["openai"]["connected"] is False
    assert body["providers"]["gemini"]["default_model"] == llm.DEFAULT_MODELS["gemini"]


def test_save_again_updates_same_row(db, client):
    client.put("/credentials/ai/openai", json={"api_key": "k1"})
    client.put("/credentials/ai/openai", json={"api_key": "k2", "model": "gpt-6-luna"})
    rows = db.tables["ai_credentials"]
    assert len(rows) == 1 and decrypt(rows[0]["secret"]) == "k2" and rows[0]["model"] == "gpt-6-luna"


def test_rejects_unknown_provider_bad_model_and_empty_key(db, client):
    assert client.put("/credentials/ai/ollama", json={"api_key": "k"}).status_code == 404
    assert client.put("/credentials/ai/gemini", json={"api_key": "k", "model": "../evil"}).status_code == 400
    assert client.put("/credentials/ai/gemini", json={"api_key": "   "}).status_code == 400
    assert db.tables["ai_credentials"] == []


def test_delete_disconnects(db, client):
    client.put("/credentials/ai/anthropic", json={"api_key": SECRET})
    assert client.delete("/credentials/ai/anthropic").json() == {"connected": False}
    assert db.tables["ai_credentials"][0]["secret"] is None
    assert client.get("/credentials/ai").json()["active"] is None


def test_generate_copy_without_key_is_400_and_never_calls_provider(db, client, provider_calls):
    res = client.post("/posts/generate-copy", json={"product_id": 1})
    assert res.status_code == 400
    assert "Credenciais" in res.json()["detail"]
    assert provider_calls == []


def test_generate_copy_uses_own_key_and_does_not_leak_it(db, client, provider_calls, caplog):
    client.put("/credentials/ai/gemini", json={"api_key": SECRET})
    with caplog.at_level(logging.DEBUG):
        res = client.post("/posts/generate-copy", json={"product_id": 1, "persona": "divertido"})

    assert res.status_code == 200 and res.json()["text"] == "Texto IA"
    assert provider_calls[0]["headers"]["x-goog-api-key"] == SECRET
    assert SECRET not in res.text and SECRET not in caplog.text


def test_generate_copy_picks_requested_or_latest_provider(db, client, provider_calls):
    client.put("/credentials/ai/gemini", json={"api_key": "g-key"})
    client.put("/credentials/ai/anthropic", json={"api_key": "a-key"})

    client.post("/posts/generate-copy", json={"product_id": 1})
    assert provider_calls[-1]["url"].startswith("https://api.anthropic.com/")

    client.post("/posts/generate-copy", json={"product_id": 1, "provider": "gemini"})
    assert "googleapis" in provider_calls[-1]["url"]

    res = client.post("/posts/generate-copy", json={"product_id": 1, "provider": "openai"})
    assert res.status_code == 400


def test_user_cannot_use_another_users_key(db):
    db.tables["ai_credentials"].append({
        "id": 1, "user_id": 99, "profile_id": None, "provider": "gemini",
        "secret": encrypt(SECRET), "status": True,
    })
    with pytest.raises(Exception) as exc:
        credentials_module.resolve_ai_key(42, None)
    assert getattr(exc.value, "status_code", None) == 400


def test_profile_cannot_use_another_profiles_key(db, client, profile_cookie):
    client.cookies.update(profile_cookie("profile-a"))
    client.put("/credentials/ai/gemini", json={"api_key": SECRET})
    assert db.tables["ai_credentials"][0]["profile_id"] == "profile-a"

    other = TestClient(app)
    other.cookies.update(profile_cookie("profile-b"))
    assert other.get("/credentials/ai").json()["providers"]["gemini"]["connected"] is False
    with pytest.raises(Exception) as exc:
        credentials_module.resolve_ai_key(42, "profile-b")
    assert getattr(exc.value, "status_code", None) == 400
    assert credentials_module.resolve_ai_key(42, "profile-a")[1] == SECRET


@pytest.mark.parametrize("provider,url,key_header,key_value", [
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
     "x-goog-api-key", SECRET),
    ("openai", "https://api.openai.com/v1/responses", "Authorization", f"Bearer {SECRET}"),
    ("anthropic", "https://api.anthropic.com/v1/messages", "x-api-key", SECRET),
])
def test_each_provider_builds_the_right_request(provider_calls, provider, url, key_header, key_value):
    text = llm.generate_product_copy({"name": "Fone"}, "casual", provider, SECRET)

    call = provider_calls[0]
    assert text == "Texto IA"
    assert call["url"] == url and call["headers"][key_header] == key_value
    if provider == "openai":
        assert call["json"]["model"] == "gpt-6-luna" and "Fone" in call["json"]["input"]
    if provider == "anthropic":
        assert call["headers"]["anthropic-version"] == "2023-06-01"
        assert call["json"]["model"] == "claude-sonnet-5-5"
        assert call["json"]["messages"][0]["role"] == "user"


def test_custom_model_is_used(provider_calls):
    llm.generate_product_copy({}, "casual", "openai", SECRET, model="gpt-6.1-sol")
    assert provider_calls[0]["json"]["model"] == "gpt-6.1-sol"


@pytest.mark.parametrize("status,body,kind", [
    (401, {"error": {"message": f"Incorrect API key provided: {SECRET}"}}, "invalid_key"),
    (400, {"error": {"status": "INVALID_ARGUMENT", "details": [{"reason": "API_KEY_INVALID"}]}}, "invalid_key"),
    (429, {"error": {"code": "insufficient_quota"}}, "quota"),
    (404, {"error": {"message": "model not found"}}, "model"),
    (500, {"error": "boom"}, "provider"),
])
def test_provider_errors_are_clear_and_never_echo_secret(monkeypatch, status, body, kind):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: httpx.Response(status, json=body))
    with pytest.raises(llm.LLMError) as exc:
        llm.check_key("openai", SECRET)
    assert exc.value.kind == kind and SECRET not in str(exc.value)


def test_network_error_is_clear(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError(f"falhou com {SECRET}")
    monkeypatch.setattr(llm.httpx, "post", boom)
    with pytest.raises(llm.LLMError) as exc:
        llm.check_key("anthropic", SECRET)
    assert exc.value.kind == "network" and SECRET not in str(exc.value)


def test_test_endpoint_records_check_without_leaking(db, client, monkeypatch, caplog):
    client.put("/credentials/ai/openai", json={"api_key": SECRET})
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: httpx.Response(401, json={"error": SECRET}))

    with caplog.at_level(logging.DEBUG):
        res = client.post("/credentials/ai/openai/test")

    assert res.status_code == 200 and res.json()["light"] == "yellow"
    assert SECRET not in res.text and SECRET not in caplog.text
    check = db.tables["credential_checks"][0]
    assert check["network"] == "ai_openai" and check["state"] == "error"
    status = client.get("/credentials/ai").json()["providers"]["openai"]
    assert status["state"] == "error"


def test_test_endpoint_ok_turns_green(db, client, provider_calls):
    client.put("/credentials/ai/gemini", json={"api_key": SECRET})
    res = client.post("/credentials/ai/gemini/test")
    assert res.json()["light"] == "green"
    assert client.get("/credentials/ai").json()["providers"]["gemini"]["light"] == "green"


def test_test_endpoint_without_key_is_400(db, client):
    assert client.post("/credentials/ai/gemini/test").status_code == 400


def test_ai_routes_require_auth():
    app.dependency_overrides.clear()
    anon = TestClient(app)
    assert anon.get("/credentials/ai").status_code == 401
    assert anon.put("/credentials/ai/gemini", json={"api_key": "k"}).status_code == 401
    assert anon.post("/credentials/ai/gemini/test").status_code == 401


def test_migration_043_is_additive_idempotent_with_rls():
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[2] / "database" / "migrations"
           / "043_create_ai_credentials_table.sql").read_text(encoding="utf-8").lower()
    assert "create table if not exists public.ai_credentials" in sql
    assert "create unique index if not exists uq_ai_credentials_user_profile_provider" in sql
    assert "enable row level security" in sql
    assert "if not exists" in sql and 'create policy "block_all_api" on public.ai_credentials' in sql
    assert "drop " not in sql and "delete from" not in sql and "truncate" not in sql

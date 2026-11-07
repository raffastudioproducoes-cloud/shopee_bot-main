"""Adaptadores dos três provedores; gestão multiusuário em test_platform_ai_contract."""
import httpx
import pytest

from apis import llm

SECRET = "sk-test-SEGREDO-123"


@pytest.fixture
def provider_calls(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        if "googleapis" in url:
            body = {"candidates": [{"content": {"parts": [
                {"text": "pensando", "thought": True}, {"text": "Texto IA"}]}}]}
        elif "openai" in url:
            body = {"output": [{"type": "reasoning"}, {"type": "message",
                               "content": [{"type": "output_text", "text": "Texto IA"}]}]}
        else:
            body = {"content": [{"type": "thinking", "thinking": ""},
                                {"type": "text", "text": "Texto IA"}]}
        return httpx.Response(200, json=body)

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    return calls


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
    assert "Credenciais" not in str(exc.value)


def test_network_error_is_clear(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError(f"falhou com {SECRET}")
    monkeypatch.setattr(llm.httpx, "post", boom)
    with pytest.raises(llm.LLMError) as exc:
        llm.check_key("anthropic", SECRET)
    assert exc.value.kind == "network" and SECRET not in str(exc.value)


def test_legacy_migration_043_keeps_rls_and_encrypted_account_history():
    from pathlib import Path
    sql = (Path(__file__).resolve().parents[2] / "database" / "migrations"
           / "043_create_ai_credentials_table.sql").read_text(encoding="utf-8").lower()
    assert "create table if not exists public.ai_credentials" in sql
    assert "enable row level security" in sql
    assert 'create policy "block_all_api" on public.ai_credentials' in sql

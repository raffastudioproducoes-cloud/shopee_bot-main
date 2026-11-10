"""S-05: senha vazada é recusada por k-anonimato, sem enviar a senha, e a falha do serviço não bloqueia."""
import hashlib

import httpx
import pytest
from fastapi import HTTPException

from api import password_breach


def _suffix_prefix(password):
    digest = hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest().upper()
    return digest[:5], digest[5:]


def _client_returning(body, seen):
    def handler(request):
        seen.append(request)
        return httpx.Response(200, text=body)
    real = httpx.Client
    return lambda **kw: real(transport=httpx.MockTransport(handler), **{k: v for k, v in kw.items() if k != "transport"})


@pytest.fixture(autouse=True)
def _real_breach_count(monkeypatch):
    # desfaz o mock do conftest para exercitar a função real (com transporte falso)
    import importlib
    monkeypatch.setattr(password_breach, "breach_count", importlib.reload(password_breach).breach_count)


def test_only_the_five_char_prefix_leaves_the_server(monkeypatch):
    prefix, suffix = _suffix_prefix("senha-vazada-123")
    seen = []
    monkeypatch.setattr(password_breach.httpx, "Client", _client_returning(f"{suffix}:42\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:0", seen))
    assert password_breach.breach_count("senha-vazada-123") == 42
    url = str(seen[0].url)
    assert url.endswith("/range/" + prefix) and suffix not in url and "senha" not in url
    assert seen[0].headers["Add-Padding"] == "true"


def test_clean_password_has_zero_count(monkeypatch):
    monkeypatch.setattr(password_breach.httpx, "Client", _client_returning("0000000000000000000000000000000000A:3", []))
    assert password_breach.breach_count("uma-senha-bem-unica-9f3k") == 0


def test_padding_lines_with_zero_count_do_not_flag(monkeypatch):
    prefix, suffix = _suffix_prefix("x-senha-padrao")
    monkeypatch.setattr(password_breach.httpx, "Client", _client_returning(f"{suffix}:0", []))
    assert password_breach.breach_count("x-senha-padrao") == 0


def test_service_down_does_not_block(monkeypatch):
    def boom(**kw):
        raise httpx.ConnectError("fora do ar")
    monkeypatch.setattr(password_breach.httpx, "Client", boom)
    assert password_breach.breach_count("qualquer-senha-1") is None   # falha aberta, sem 500


@pytest.mark.anyio
async def test_breached_password_is_rejected_with_422(monkeypatch):
    monkeypatch.setattr(password_breach, "breach_count", lambda p: 1000)
    with pytest.raises(HTTPException) as err:
        await password_breach.ensure_password_not_breached("123456789")
    assert err.value.status_code == 422 and "vazamentos" in err.value.detail


@pytest.mark.anyio
async def test_unknown_result_is_allowed(monkeypatch):
    monkeypatch.setattr(password_breach, "breach_count", lambda p: None)
    await password_breach.ensure_password_not_breached("Qualquer-Senha-9x")

"""Campanha: validação OAuth antes do envio não pode falhar por causa do event loop.

Regressão 2026-11-12: com monkey-patch do gevent, a "thread" do timeout era um
greenlet no mesmo thread do SO de um loop em execução, e `asyncio.run` levantava
RuntimeError -> toda campanha era marcada como credencial inválida.
"""
import asyncio
import os
import subprocess
import sys

import pytest

# api/config.py aborta o import sem estes valores (mesmos de tests/api/conftest.py).
os.environ.setdefault("APP_ENCRYPTION_KEY", "e7lc8f3AsY0VNg7Kpy1K5umJirUK6jwqkJg7_xhn0IY=")
os.environ.setdefault("API_SECRET_KEY", "test-only-api-secret-key-0123456789abcdef-0123456789abcdef-padding-64b")

from shopee_bot.api.routers import credentials as cred
from shopee_bot.scheduler import campaign_dispatch


@pytest.fixture
def fake_validation(monkeypatch):
    state = {"result": {"state": "ok", "message": ""}}

    async def fake(network, payload):
        await asyncio.sleep(0)
        return state["result"]

    monkeypatch.setattr(cred, "validate_network_credential", fake)
    monkeypatch.setattr(cred, "_test_payload", lambda *a: {"access_token": "t"})
    monkeypatch.setattr(cred, "_persist_refreshed_tokens", lambda *a: None)
    return state


def test_valid_credential_passes(fake_validation):
    assert campaign_dispatch._validated_credentials("threads", 1, None) is True


def test_invalid_credential_fails(fake_validation):
    fake_validation["result"] = {"state": "error", "message": "token expirado"}
    assert campaign_dispatch._validated_credentials("threads", 1, None) is False


def test_validation_exception_fails_and_logs_message(fake_validation, monkeypatch):
    def boom(*a):
        raise ValueError("falha-xyz")

    monkeypatch.setattr(cred, "_test_payload", boom)
    logged = []
    monkeypatch.setattr(campaign_dispatch.logger, "warning", lambda *a, **k: logged.append(a))
    assert campaign_dispatch._validated_credentials("threads", 1, None) is False
    assert "falha-xyz" in str(logged[0])


# Em produção o gevent monkey-patch está ativo (o conftest.py raiz faz o mesmo, mas
# aqui é excluído por --confcutdir); por isso o cenário roda num processo à parte.
_SCRIPT = """
from gevent import monkey; monkey.patch_all()
import asyncio, sys, types
pkg = types.ModuleType("shopee_bot"); pkg.__path__ = [sys.argv[1]]; sys.modules["shopee_bot"] = pkg
from shopee_bot.api.routers.credentials import _call_with_timeout

async def validate():
    return {"state": "ok"}

async def caller():
    return _call_with_timeout(lambda: asyncio.run(validate()))

print(asyncio.run(caller()))
"""


def test_validation_inside_running_loop_with_gevent_patch():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proc = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", _SCRIPT, root],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    assert "'state': 'ok'" in proc.stdout

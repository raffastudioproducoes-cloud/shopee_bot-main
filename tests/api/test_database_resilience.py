"""Conexão morta com o banco (`Broken pipe`) não pode virar 500 na primeira chamada."""
import httpx
import pytest

from api.database import harden_http_session


class _Flaky(httpx.BaseTransport):
    def __init__(self, failures):
        self.failures, self.calls = list(failures), 0

    def handle_request(self, request):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)(("falha simulada"), request=request)
        return httpx.Response(200, json={"ok": True}, request=request)


def _client(failures):
    transport = _Flaky(failures)
    return harden_http_session(httpx.Client(transport=transport, base_url="https://db.test")), transport


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_write_error_is_retried_once_for_any_method(method):
    client, transport = _client([httpx.WriteError])
    assert client.request(method, "/x").status_code == 200
    assert transport.calls == 2          # o pedido nem saiu: repetir é seguro


def test_second_failure_is_not_hidden():
    client, transport = _client([httpx.WriteError, httpx.WriteError])
    with pytest.raises(httpx.WriteError):
        client.get("/x")
    assert transport.calls == 2          # só uma repetição


def test_read_error_retries_reads_but_never_writes():
    client, transport = _client([httpx.ReadError])
    assert client.get("/x").status_code == 200 and transport.calls == 2
    client, transport = _client([httpx.ReadError])
    with pytest.raises(httpx.ReadError):
        client.post("/x", json={})       # o servidor pode ter gravado: não repetir
    assert transport.calls == 1


def test_healthy_call_is_not_repeated():
    client, transport = _client([])
    assert client.get("/x").json() == {"ok": True} and transport.calls == 1

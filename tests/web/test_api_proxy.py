"""Testa o proxy /api/* -> FastAPI interno (web/routes/api_proxy.py).

Mocka requests.request pra não depender de um uvicorn real rodando em
127.0.0.1:8001 — só confirma que o blueprint repassa método, query,
corpo, headers e status corretamente.
"""

from unittest.mock import patch

import requests


class _FakeUpstreamResponse:
    def __init__(self, status_code=200, content=b'{"ok":true}',
                 headers=None):
        self.status_code = status_code
        self.content = content
        headers = headers or {"Content-Type": "application/json"}
        self.raw = type("Raw", (), {"headers": headers})()


def test_proxy_forwards_get_and_status(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.return_value = _FakeUpstreamResponse(
            status_code=200, content=b'{"status":"ok"}'
        )
        res = client.get("/api/health?x=1")

    assert res.status_code == 200
    assert res.data == b'{"status":"ok"}'
    called = mock_req.call_args
    assert called.kwargs["method"] == "GET"
    assert called.kwargs["url"] == "http://127.0.0.1:8001/health"
    assert called.kwargs["params"]["x"] == "1"


def test_proxy_forwards_post_body_and_error_status(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.return_value = _FakeUpstreamResponse(
            status_code=401, content=b'{"detail":"unauthorized"}'
        )
        res = client.post(
            "/api/auth/login",
            data=b'{"user":"x"}',
            content_type="application/json",
        )

    assert res.status_code == 401
    assert res.data == b'{"detail":"unauthorized"}'
    called = mock_req.call_args
    assert called.kwargs["method"] == "POST"
    assert called.kwargs["data"] == b'{"user":"x"}'


def test_proxy_forwards_meta_form_body_content_type_without_csrf(client):
    body = b"signed_request=a.b"
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.return_value = _FakeUpstreamResponse(
            status_code=200, content=b'{"status":"received"}'
        )
        res = client.post(
            "/api/meta/data-deletion",
            data=body,
            content_type="application/x-www-form-urlencoded",
        )

    assert res.status_code == 200
    assert res.data == b'{"status":"received"}'
    called = mock_req.call_args
    assert called.kwargs["url"] == "http://127.0.0.1:8001/meta/data-deletion"
    assert called.kwargs["data"] == body
    assert called.kwargs["headers"]["Content-Type"].startswith("application/x-www-form-urlencoded")


def test_proxy_returns_502_when_upstream_unreachable(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.side_effect = requests.ConnectionError("boom")
        res = client.get("/api/health")

    assert res.status_code == 502
    assert res.get_json()["error"]

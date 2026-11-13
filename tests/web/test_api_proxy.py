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


def test_product_media_post_waits_for_ffmpeg_and_storage_without_widening_other_routes(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.return_value = _FakeUpstreamResponse()
        media = client.post("/api/products/42/media", data=b"mp4")
        regular = client.post("/api/posts/42/media", data=b"mp4")
        other = client.get("/api/products/42/media")

    assert media.status_code == regular.status_code == other.status_code == 200
    assert mock_req.call_args_list[0].kwargs["timeout"] == (5, 180)
    assert mock_req.call_args_list[1].kwargs["timeout"] == 30
    assert mock_req.call_args_list[2].kwargs["timeout"] == 30


def test_product_media_timeout_returns_actionable_504(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.side_effect = requests.ReadTimeout("internal host and credentials")
        res = client.post("/api/products/42/media", data=b"mp4")

    assert res.status_code == 504
    assert "galeria" in res.get_json()["error"]
    assert "credentials" not in res.get_data(as_text=True)


def test_regular_api_timeout_still_uses_short_deadline(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.side_effect = requests.ReadTimeout("upstream")
        res = client.get("/api/health")

    assert res.status_code == 504
    assert "não respondeu" in res.get_json()["error"]
    assert mock_req.call_args.kwargs["timeout"] == 30


def test_campaign_activation_has_longer_deadline_only_for_activate_post(client):
    draft = "3f2b8c1e-0a4d-4c55-9b7e-1d2c3b4a5f60"
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.return_value = _FakeUpstreamResponse()
        activate = client.post(f"/api/campaigns/drafts/{draft}/activate", data=b"{}")
        save = client.post(f"/api/campaigns/drafts/{draft}", data=b"{}")
        listing = client.get(f"/api/campaigns/drafts/{draft}/activate")

    assert activate.status_code == save.status_code == listing.status_code == 200
    assert mock_req.call_args_list[0].kwargs["timeout"] == (5, 90)
    assert mock_req.call_args_list[1].kwargs["timeout"] == 30
    assert mock_req.call_args_list[2].kwargs["timeout"] == 30


def test_campaign_activation_timeout_returns_actionable_504(client):
    draft = "3f2b8c1e-0a4d-4c55-9b7e-1d2c3b4a5f60"
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.side_effect = requests.ReadTimeout("internal host and credentials")
        res = client.post(f"/api/campaigns/drafts/{draft}/activate", data=b"{}")

    assert res.status_code == 504
    assert "seção 06" in res.get_json()["error"]
    assert "credentials" not in res.get_data(as_text=True)


def test_click_redirect_route_forwards_302_without_following(client):
    token = "AbCdEfGhIjKlMnOpQrStUv"
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.return_value = _FakeUpstreamResponse(
            status_code=302, content=b"", headers={"Location": "https://s.shopee.com.br/abc"}
        )
        res = client.get(f"/r/{token}")
    assert res.status_code == 302
    assert res.headers["Location"] == "https://s.shopee.com.br/abc"
    called = mock_req.call_args
    assert called.kwargs["url"] == f"http://127.0.0.1:8001/r/{token}"
    assert called.kwargs["allow_redirects"] is False


def test_click_redirect_route_rejects_malformed_token_without_upstream(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        res = client.get("/r/curto")
    assert res.status_code == 404
    mock_req.assert_not_called()

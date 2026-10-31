"""Contract: Render metrics use documented minimal params and sanitized errors."""
import asyncio

import httpx
import pytest

from api import admin_metrics


def _setup(monkeypatch, handler):
    original_client = httpx.AsyncClient
    monkeypatch.setenv("RENDER_METRICS_API_KEY", "private-test-token")
    monkeypatch.delenv("RENDER_ADMIN_SERVICE_ID", raising=False)
    monkeypatch.setattr(
        admin_metrics.httpx, "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_five_render_metrics_use_only_resource(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        assert dict(request.url.params) == {"resource": "srv-da6vrla6iojc7380a13g"}
        assert request.headers["Authorization"] == "Bearer private-test-token"
        assert request.url.host == "api.render.com"
        return httpx.Response(200, json=[{
            "unit": "bytes", "values": [
                {"timestamp": "2026-10-30T20:00:00Z", "value": 1048576},
            ],
        }])

    _setup(monkeypatch, handler)
    result = asyncio.run(admin_metrics._render_snapshot())
    assert result.status == "available"
    assert result.diagnostic is None
    assert len(calls) == 5
    assert {path.rsplit("/", 1)[-1] for path in calls} == {
        "cpu", "memory", "cpu-limit", "memory-limit", "bandwidth",
    }


@pytest.mark.parametrize("code,expected", [
    (400, "bad_request"),
    (401, "api_rejected"),
    (403, "api_rejected"),
    (503, "provider_error"),
])
def test_render_http_errors_are_safe_and_distinct(monkeypatch, code, expected):
    def handler(_request):
        return httpx.Response(code, json={
            "message": "secret-do-not-expose", "token": "also-private",
        })

    _setup(monkeypatch, handler)
    result = asyncio.run(admin_metrics._render_snapshot())
    assert result.status == "unavailable"
    assert result.diagnostic == expected
    assert len(result.missing_metrics) == 5
    assert "secret-do-not-expose" not in result.model_dump_json()
    assert "private-test-token" not in result.model_dump_json()


def test_missing_samples_are_not_zero(monkeypatch):
    _setup(monkeypatch, lambda _req: httpx.Response(200, json=[]))
    result = asyncio.run(admin_metrics._render_snapshot())
    assert result.status == "unavailable"
    assert result.diagnostic == "no_samples"
    assert result.cpu is None

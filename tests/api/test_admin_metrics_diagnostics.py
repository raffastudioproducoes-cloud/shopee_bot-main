"""Safe, honest status diagnostics for administrative observability."""
import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from api import admin_metrics


def test_database_failure_is_classified_without_leaking_error_details(monkeypatch):
    db = MagicMock()
    db.rpc.return_value.execute.side_effect = RuntimeError("token=private-value")
    monkeypatch.setattr(admin_metrics, "supabase", db)
    snapshot, latency, diagnostic = asyncio.run(admin_metrics._database_snapshot(7))
    assert snapshot is None
    assert latency >= 0
    assert diagnostic == "provider_error"


@pytest.mark.parametrize("exc,expected", [
    (asyncio.TimeoutError(), "timeout"),
    (ValueError("private"), "invalid_response"),
    (RuntimeError("private"), "provider_error"),
])
def test_database_failure_categories_are_sanitized(exc, expected):
    assert admin_metrics._database_diagnostic(exc) == expected


def test_render_unconfigured_is_explicit(monkeypatch):
    monkeypatch.delenv("RENDER_METRICS_API_KEY", raising=False)
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    result = asyncio.run(admin_metrics._render_snapshot())
    assert result.status == "not_configured"
    assert result.diagnostic == "not_configured"


def test_render_permission_error_is_not_transmitted(monkeypatch):
    real_client = httpx.AsyncClient

    def handler(request):
        return httpx.Response(403, text="secret-should-not-be-returned")

    monkeypatch.setenv("RENDER_METRICS_API_KEY", "private-test-token")
    monkeypatch.setattr(admin_metrics.httpx, "AsyncClient", lambda **kwargs:
                        real_client(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(admin_metrics._render_snapshot())
    assert result.status == "unavailable"
    assert result.diagnostic == "api_rejected"
    assert len(result.missing_metrics) == 5
    assert "private-test-token" not in result.model_dump_json()
    assert "secret-should-not-be-returned" not in result.model_dump_json()


def test_geography_reports_not_configured_not_fake_data():
    result = admin_metrics.GeographyMetrics()
    assert result.status == "not_configured"
    assert result.regions == []

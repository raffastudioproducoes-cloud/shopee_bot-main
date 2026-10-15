"""Métricas globais: somente ADMIN e somente agregados na resposta."""
from unittest.mock import MagicMock
import asyncio
import httpx

import pytest
from fastapi.testclient import TestClient

from api import database
from api.config import settings
from api.main import app
from api.routers.auth import get_current_user_id


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.delenv("RENDER_METRICS_API_KEY", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    yield
    app.dependency_overrides.clear()


def fake_client(monkeypatch, role="ADMIN"):
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data={"access": role})
    monkeypatch.setattr(database, "get_supabase", lambda: client)
    app.dependency_overrides[get_current_user_id] = lambda: "test-admin"
    return client


def snapshot():
    return {
        "counts": {"accounts": 7, "new_accounts": 2, "deleted_accounts": 1,
                   "free_accounts": 5, "plus_accounts": 1, "premium_accounts": 1,
                   "active_accounts": 3, "requests": 100, "errors": 2,
                   "avg_latency_ms": 12.5, "p95_latency_ms": 35},
        "daily": [{"date": "2026-10-15", "registrations": 2, "deletions": 1, "requests": 20}],
        "database": {"database_bytes": 1048576, "connections": 4, "max_connections": 100},
    }


def test_metrics_requires_authentication():
    assert TestClient(app).get("/admin/metrics").status_code == 401


def test_metrics_rejects_user_before_reading_snapshot(monkeypatch):
    db = fake_client(monkeypatch, "USER")
    assert TestClient(app).get("/admin/metrics").status_code == 403
    db.rpc.assert_not_called()


def test_render_aggregates_instances_and_discards_labels():
    from api.admin_metrics import parse_render_metric
    result = parse_render_metric([
        {"unit": "GB", "labels": [{"value": "private-service-id"}], "values": [{"timestamp": "2026-10-15T05:00:00Z", "value": 1}]},
        {"unit": "GB", "values": [{"timestamp": "2026-10-15T05:00:00Z", "value": 2}]},
    ])
    assert result.value == 3
    assert "private-service-id" not in result.model_dump_json()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_render_rejects_invalid_samples(value):
    from api.admin_metrics import parse_render_metric
    with pytest.raises(ValueError):
        parse_render_metric([{"unit": "CPU", "values": [{"timestamp": "2026-10-15T05:00:00Z", "value": value}]}])


@pytest.mark.parametrize("unit", ["cpu", "bytes", "mb"])
def test_render_accepts_units_observed_in_live_plugin(unit):
    from api.admin_metrics import parse_render_metric
    result = parse_render_metric([{"unit": unit, "values": [{"timestamp": "2026-10-15T05:00:00Z", "value": 0.15}]}])
    assert result.unit == unit
    assert len(result.timestamps) == len(result.values) == 1


@pytest.mark.parametrize("memory_status, expected", [(200, "available"), (403, "partial")])
def test_render_configured_transport_is_bounded_and_private(monkeypatch, memory_status, expected):
    from api import admin_metrics
    real_client = httpx.AsyncClient
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer synthetic-test-token"
        assert request.url.host == "api.render.com"
        assert request.url.params["resolutionSeconds"] == "3600"
        assert request.extensions["timeout"]["read"] == 4
        if request.url.path.endswith("memory") and memory_status != 200:
            return httpx.Response(memory_status, text="synthetic-test-token")
        return httpx.Response(200, json=[{"unit": "CPU", "labels": [{"value": "private-service-id"}], "values": [{"timestamp": "2026-10-15T05:00:00Z", "value": 0.5}]}])
    monkeypatch.setenv("RENDER_METRICS_API_KEY", "synthetic-test-token")
    monkeypatch.setenv("RENDER_SERVICE_ID", "private-service-id")
    monkeypatch.setattr(admin_metrics.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(admin_metrics._render_snapshot())
    assert result.status == expected
    assert len(calls) == 5
    assert "private-service-id" not in result.model_dump_json()
    assert "synthetic-test-token" not in result.model_dump_json()


def test_metrics_returns_only_aggregates_and_honest_availability(monkeypatch):
    db = fake_client(monkeypatch)
    data = snapshot()
    data["password"] = "never-expose-this"
    data["counts"]["user_id"] = "never-expose-this"
    db.rpc.return_value.execute.return_value = MagicMock(data=data)
    monkeypatch.setattr(settings, "request_logging_enabled", True)
    response = TestClient(app).get("/admin/metrics", params={"days": 7})
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["accounts"] == 7
    assert body["counts"]["active_accounts"] == 3
    assert body["supabase"]["database_bytes"] == 1048576
    assert body["render"]["status"] == "not_configured"
    assert "never-expose-this" not in response.text
    assert body["unavailable"]["paying_accounts"]
    assert body["unavailable"]["location"]
    db.rpc.assert_called_once_with("admin_metrics_snapshot", {"lookback_days": 7})


def test_disabled_logging_does_not_claim_users_are_online(monkeypatch):
    db = fake_client(monkeypatch)
    db.rpc.return_value.execute.return_value = MagicMock(data=snapshot())
    monkeypatch.setattr(settings, "request_logging_enabled", False)
    assert TestClient(app).get("/admin/metrics").json()["counts"]["active_accounts"] is None


def test_missing_migration_does_not_leak_error_or_return_fake_zeroes(monkeypatch):
    db = fake_client(monkeypatch)
    db.rpc.return_value.execute.side_effect = RuntimeError("password=never-expose-this")
    response = TestClient(app).get("/admin/metrics")
    assert response.status_code == 200
    assert response.json()["counts"] is None
    assert response.json()["supabase"]["status"] == "unavailable"
    assert "never-expose-this" not in response.text


@pytest.mark.parametrize("days", [0, 6, 91, "invalid"])
def test_metrics_bounds_query_period(days, monkeypatch):
    db = fake_client(monkeypatch)
    assert TestClient(app).get("/admin/metrics", params={"days": days}).status_code == 422
    db.rpc.assert_not_called()

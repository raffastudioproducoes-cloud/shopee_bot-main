"""Admin-only queue diagnostics: aggregate values, failures and access isolation."""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api import database
from api.main import app
from api.routers.auth import get_current_user_id


def _client(monkeypatch, access="ADMIN"):
    app.dependency_overrides.clear()
    fake = MagicMock()
    fake.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data={"access": access})
    monkeypatch.setattr(database, "get_supabase", lambda: fake)
    app.dependency_overrides[get_current_user_id] = lambda: "synthetic-admin"
    return fake


def test_queue_health_requires_authentication():
    app.dependency_overrides.clear()
    assert TestClient(app).get("/admin/queue-health").status_code == 401


def test_queue_health_blocks_non_admin_before_rpc(monkeypatch):
    db = _client(monkeypatch, "USER")
    try:
        assert TestClient(app).get("/admin/queue-health").status_code == 403
        db.rpc.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_queue_health_only_returns_aggregate_fields(monkeypatch):
    db = _client(monkeypatch)
    db.rpc.return_value.execute.return_value = MagicMock(data={
        "counts": {
            "total": 4, "pending": 0, "running": 0, "unknown": 1,
            "failed": 0, "succeeded": 3, "manually_confirmed": 0,
            "multiple_attempts": 0
        },
        "oldest_unknown_minutes": 190,
        "oldest_running_minutes": None,
        "last_started_at": "2026-10-30T22:46:00Z",
        "collected_at": "2026-10-31T02:00:00Z",
        "user_id": "user-must-not-leak",
        "last_error": "token-must-not-leak",
    })
    try:
        result = TestClient(app).get("/admin/queue-health")
        assert result.status_code == 200
        body = result.json()
        assert body["status"] == "available"
        assert body["counts"]["unknown"] == 1
        assert body["counts"]["succeeded"] == 3
        assert "user-must-not-leak" not in result.text
        assert "token-must-not-leak" not in result.text
        db.rpc.assert_called_once_with("admin_queue_health_snapshot")
    finally:
        app.dependency_overrides.clear()


def test_queue_rpc_failure_never_returns_fake_zero(monkeypatch):
    db = _client(monkeypatch)
    db.rpc.return_value.execute.side_effect = RuntimeError("password=never-leak")
    try:
        result = TestClient(app).get("/admin/queue-health")
        assert result.status_code == 200
        assert result.json()["status"] == "unavailable"
        assert result.json()["counts"] is None
        assert "never-leak" not in result.text
    finally:
        app.dependency_overrides.clear()

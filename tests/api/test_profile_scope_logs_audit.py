"""Multi-perfil: logs/auditoria gravam profile_id do perfil ativo; GET /logs filtra por ele."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import audit_log as audit_log_module
from api import database as database_module
from api import middleware as middleware_module
from api.audit_trail import record_audit_event
from api.config import settings
from api.main import app
from api.routers import logs as logs_module
from api.routers.auth import get_current_user_id


@pytest.fixture(autouse=True)
def _restore_flag():
    original = settings.request_logging_enabled
    yield
    settings.request_logging_enabled = original
    app.dependency_overrides.clear()


def test_audit_event_stores_profile_id_only_when_given(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    record_audit_event("product", "1", "42", "product_deleted", {"a": 1}, None, profile_id="profile-a")
    assert fake_client.table.return_value.insert.call_args[0][0]["profile_id"] == "profile-a"

    record_audit_event("product", "1", "42", "product_deleted", {"a": 1}, None)
    assert "profile_id" not in fake_client.table.return_value.insert.call_args[0][0]


def test_log_action_stores_profile_id(monkeypatch):
    settings.request_logging_enabled = True
    fake_client = MagicMock()
    monkeypatch.setattr(audit_log_module, "get_supabase", lambda: fake_client)

    audit_log_module.log_action("post_published", "x", user_id=1, profile_id="profile-a")

    assert fake_client.table.return_value.insert.call_args[0][0]["profile_id"] == "profile-a"


def test_log_action_replaces_lone_surrogates_so_httpx_can_encode(monkeypatch):
    settings.request_logging_enabled = True
    fake_client = MagicMock()
    monkeypatch.setattr(audit_log_module, "get_supabase", lambda: fake_client)

    audit_log_module.log_action("post_publish_failed", "error=a\udcffb", user_id=1)

    row = fake_client.table.return_value.insert.call_args[0][0]
    row["error"].encode("utf-8")
    assert row["error"].startswith("error=a") and row["error"].endswith("b")


def test_request_middleware_logs_profile_claim(monkeypatch, profile_cookie):
    settings.request_logging_enabled = True
    fake_client = MagicMock()
    monkeypatch.setattr(middleware_module, "get_supabase", lambda: fake_client)
    client = TestClient(app)
    client.cookies.update(profile_cookie("profile-a"))

    client.get("/credentials")

    assert fake_client.table.return_value.insert.call_args[0][0]["profile_id"] == "profile-a"


def test_logs_endpoint_filters_by_profile_id(fake_db, monkeypatch):
    db = fake_db({
        "users": [{"id": 1, "access": "ADMIN"}],
        "request_logs": [
            {"id": 1, "profile_id": "profile-a", "created_at": "2026-01-01", "method": "GET"},
            {"id": 2, "profile_id": "profile-b", "created_at": "2026-01-02", "method": "GET"},
        ],
    })
    monkeypatch.setattr(logs_module, "supabase", db)
    app.dependency_overrides[get_current_user_id] = lambda: 1
    client = TestClient(app)

    only_a = client.get("/logs", params={"profile_id": "profile-a"}).json()["data"]
    everything = client.get("/logs").json()["data"]

    assert [r["id"] for r in only_a] == [1]
    assert {r["id"] for r in everything} == {1, 2}

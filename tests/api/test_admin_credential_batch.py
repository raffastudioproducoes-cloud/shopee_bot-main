"""Lote de diagnóstico ADMIN sem vazamento de segredos ou testes fictícios."""
import asyncio
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api import database
from api.main import app
from api.routers import admin, credentials, platform_ai, platform_shopee
from api.routers.auth import get_current_user_id


def test_only_admin_can_execute_batch(monkeypatch, fake_db):
    monkeypatch.setattr(database, "get_supabase", lambda: fake_db({
        "users": [{"id": "not-admin", "access": "USER"}],
    }))
    app.dependency_overrides[get_current_user_id] = lambda: "not-admin"
    try:
        response = TestClient(app).post("/admin/credentials/test-all")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_single_rate_limit_skips_unconfigured_and_audits(monkeypatch):
    attempts, calls, logs = [], [], []
    monkeypatch.setattr(credentials, "_check_test_rate_limit", lambda uid: attempts.append(uid))
    monkeypatch.setattr(credentials, "list_credentials", AsyncMock(return_value={
        "facebook": {"connected": True}, "x": {"connected": True},
        "instagram": {"connected": False}, "kwai": {"connected": False},
        "threads": {"connected": False}, "tiktok": {"connected": False},
        "shopee": {"connected": True},  # ID individual não é uma chave a testar.
    }))
    monkeypatch.setattr(platform_ai, "admin_platform_ai_status", AsyncMock(return_value={
        "active": "gemini", "providers": {"gemini": {"connected": True}},
    }))
    monkeypatch.setattr(platform_shopee, "admin_shopee_status", AsyncMock(return_value={"connected": True}))

    async def fake_network(network, admin_id, profile_id):
        calls.append((network, admin_id, profile_id))
        if network == "x":
            raise RuntimeError("access_token=SECRET")
        return {"light": "green", "checked_at": "2026-11-07T12:00:00Z"}

    async def ok(*_args):
        return {"light": "green", "checked_at": "2026-11-07T12:00:00Z"}

    monkeypatch.setattr(credentials, "_execute_credential_test", fake_network)
    monkeypatch.setattr(platform_ai, "_execute_platform_ai_test", ok)
    monkeypatch.setattr(platform_shopee, "_execute_platform_shopee_test", ok)
    monkeypatch.setattr(admin, "log_action", lambda *args, **kwargs: logs.append((args, kwargs)))

    result = asyncio.run(admin.test_all_connections(admin="root", profile_id="profile-1"))
    assert attempts == ["root"]
    assert sorted(name for name, *_ in calls) == ["facebook", "x"]
    assert result["tested"] == 4 and result["skipped"] == 4
    assert result["results"]["ai"]["state"] == "ok"
    assert result["results"]["shopee"]["state"] == "ok"
    assert result["results"]["x"]["state"] == "error"
    assert result["results"]["instagram"]["state"] == "skipped"
    assert len(logs) == 5  # uma ação por resultado + resumo do lote
    assert ('admin_credentials_test_x_error',) in [args for args, _ in logs]
    assert all(kwargs.get('force') is True for _, kwargs in logs)
    assert "SECRET" not in str(result) + str(logs)


def test_batch_with_no_connections_never_calls_providers(monkeypatch):
    monkeypatch.setattr(credentials, "_check_test_rate_limit", lambda uid: None)
    monkeypatch.setattr(credentials, "list_credentials", AsyncMock(return_value={}))
    monkeypatch.setattr(platform_ai, "admin_platform_ai_status", AsyncMock(return_value={
        "active": None, "providers": {},
    }))
    monkeypatch.setattr(platform_shopee, "admin_shopee_status", AsyncMock(return_value={"connected": False}))
    monkeypatch.setattr(admin, "log_action", lambda *a, **k: None)
    monkeypatch.setattr(credentials, "_execute_credential_test", AsyncMock(side_effect=AssertionError("não testar")))
    result = asyncio.run(admin.test_all_connections(admin="root", profile_id=None))
    assert result["tested"] == 0 and result["skipped"] == 8
    assert {row["state"] for row in result["results"].values()} == {"skipped"}

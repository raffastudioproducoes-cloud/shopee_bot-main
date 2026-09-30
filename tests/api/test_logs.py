"""Testes de GET /logs (api/routers/logs.py) — admin-only, paginado, sanitizado."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers.auth import get_current_user_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


def _mock_supabase(monkeypatch, execute_results):
    """Mesmo padrão de tests/api/test_credentials.py."""
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.ilike.return_value = query
    query.gte.return_value = query
    query.lte.return_value = query
    query.single.return_value = query
    query.maybe_single.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.side_effect = [MagicMock(data=d, count=c) for d, c in execute_results]
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return query


class TestAuth:
    def test_requires_auth(self, client):
        res = client.get("/logs")
        assert res.status_code == 401

    def test_non_admin_gets_403(self, client, monkeypatch):
        app.dependency_overrides[get_current_user_id] = lambda: 7
        _mock_supabase(monkeypatch, [({"access": "USER"}, None)])

        res = client.get("/logs")

        assert res.status_code == 403


class TestAdminAccess:
    def test_admin_sees_sanitized_paginated_data(self, client, monkeypatch):
        app.dependency_overrides[get_current_user_id] = lambda: 1
        rows = [
            {
                "id": 1,
                "user_id": 1,
                "username": "rafa",
                "method": "GET",
                "path": "/credentials",
                "action": None,
                "status_code": 200,
                "duration_ms": 12,
                "error": 'falha: {"password": "hunter2"}',
                "redirect_to": None,
                "client_ip": "127.0.0.1",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        _mock_supabase(
            monkeypatch,
            [
                ({"access": "ADMIN"}, None),  # _require_admin
                (rows, 1),  # list query
            ],
        )

        res = client.get("/logs?limit=10&offset=0")

        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert body["limit"] == 10
        assert body["offset"] == 0
        assert "hunter2" not in body["data"][0]["error"]
        assert "***REDACTED***" in body["data"][0]["error"]

    def test_pagination_params_forwarded(self, client, monkeypatch):
        app.dependency_overrides[get_current_user_id] = lambda: 1
        query = _mock_supabase(
            monkeypatch,
            [
                ({"access": "ADMIN"}, None),
                ([], 0),
            ],
        )

        res = client.get("/logs?limit=5&offset=15")

        assert res.status_code == 200
        query.range.assert_called_with(15, 19)

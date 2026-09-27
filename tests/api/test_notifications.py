"""Testes do router de notificações (FastAPI). Expõe `activities` pro sino do TopBar."""

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


@pytest.fixture
def auth_client():
    """Cliente autenticado (user_id=42) com Supabase mockado."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


def _mock_supabase(monkeypatch, rows):
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.lt.return_value = query
    query.execute.return_value = MagicMock(data=rows)
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return query


class TestNotificationsAuthRequirement:
    def test_list_requires_auth(self, client):
        res = client.get("/notifications")
        assert res.status_code == 401
        assert res.json()["detail"] == "Não autenticado"


class TestNotificationsList:
    def test_serializes_activity_type_fields(self, auth_client, monkeypatch):
        _mock_supabase(
            monkeypatch,
            [
                {
                    "id": 1,
                    "metadata": {"post_id": 7},
                    "created_at": "2026-09-27T20:00:00",
                    "activity_types": {"name": "bot_post_success", "description": "Postagem realizada."},
                },
            ],
        )

        res = auth_client.get("/notifications")

        assert res.status_code == 200
        body = res.json()
        assert body["next_cursor"] is None
        assert body["data"] == [
            {
                "id": 1,
                "type": "bot_post_success",
                "description": "Postagem realizada.",
                "metadata": {"post_id": 7},
                "created_at": "2026-09-27T20:00:00",
            }
        ]

    def test_missing_activity_type_join_does_not_crash(self, auth_client, monkeypatch):
        """LEFT JOIN pode não casar (activity_types deletado) — activity_types vem None."""
        _mock_supabase(
            monkeypatch,
            [{"id": 2, "metadata": {}, "created_at": "2026-09-27T20:00:00", "activity_types": None}],
        )

        res = auth_client.get("/notifications")

        assert res.status_code == 200
        assert res.json()["data"][0]["type"] is None
        assert res.json()["data"][0]["description"] is None

    def test_next_cursor_set_when_page_is_full(self, auth_client, monkeypatch):
        rows = [
            {
                "id": i,
                "metadata": {},
                "created_at": f"2026-09-27T20:0{i}:00",
                "activity_types": {"name": "scheduler_info", "description": "Agendador informa."},
            }
            for i in range(2)
        ]
        query = _mock_supabase(monkeypatch, rows)

        res = auth_client.get("/notifications?limit=2")

        assert res.status_code == 200
        assert res.json()["next_cursor"] == "2026-09-27T20:01:00"
        query.limit.assert_called_with(2)

    def test_cursor_param_filters_by_created_at(self, auth_client, monkeypatch):
        query = _mock_supabase(monkeypatch, [])

        auth_client.get("/notifications?cursor=2026-09-27T20:00:00")

        query.lt.assert_called_with("created_at", "2026-09-27T20:00:00")

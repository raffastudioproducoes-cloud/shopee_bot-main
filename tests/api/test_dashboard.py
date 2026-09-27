"""Testes do router de dashboard (FastAPI). Contagens agregadas do painel."""

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


def _mock_supabase(monkeypatch, counts: dict):
    """Mocka `supabase.table(name).select(...).eq(...)[.is_(...)].limit(1).execute()`
    devolvendo `count=counts[name]` (default 0) por tabela. Uma query mock por
    nome de tabela (cacheada), não uma nova a cada chamada — senão inspecionar
    `.is_` etc depois do request pega um mock que nunca foi de fato usado."""
    fake_client = MagicMock()
    queries: dict = {}

    def table_side_effect(name):
        if name not in queries:
            query = MagicMock()
            query.select.return_value = query
            query.eq.return_value = query
            query.is_.return_value = query
            query.limit.return_value = query
            query.execute.return_value = MagicMock(count=counts.get(name, 0))
            queries[name] = query
        return queries[name]

    fake_client.table.side_effect = table_side_effect
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return fake_client


class TestDashboardAuthRequirement:
    def test_stats_requires_auth(self, client):
        res = client.get("/dashboard/stats")
        assert res.status_code == 401
        assert res.json()["detail"] == "Não autenticado"


class TestDashboardStats:
    def test_returns_counts_per_table(self, auth_client, monkeypatch):
        fake_client = _mock_supabase(
            monkeypatch,
            {"products": 3, "posts": 2, "product_lists": 1, "schedulers": 4},
        )

        res = auth_client.get("/dashboard/stats")

        assert res.status_code == 200
        assert res.json() == {
            "products_count": 3,
            "posts_count": 2,
            "lists_count": 1,
            "scheduled_posts": 4,
        }
        fake_client.table.assert_any_call("products")
        fake_client.table.assert_any_call("posts")
        fake_client.table.assert_any_call("product_lists")
        fake_client.table.assert_any_call("schedulers")

    def test_posts_count_filters_by_post_id_null(self, auth_client, monkeypatch):
        """posts_count conta só threads (heads), não cada parte — mesmo
        critério usado em GET /posts."""
        fake_client = _mock_supabase(monkeypatch, {"posts": 5})

        auth_client.get("/dashboard/stats")

        posts_query = fake_client.table("posts")
        posts_query.is_.assert_called_with("post_id", "null")

    def test_none_count_from_supabase_is_treated_as_zero(self, auth_client, monkeypatch):
        """Postgrest pode devolver count=None (ex: sem header Content-Range);
        a rota nunca deve propagar `None` pro frontend."""
        fake_client = MagicMock()

        def table_side_effect(name):
            query = MagicMock()
            query.select.return_value = query
            query.eq.return_value = query
            query.is_.return_value = query
            query.limit.return_value = query
            query.execute.return_value = MagicMock(count=None)
            return query

        fake_client.table.side_effect = table_side_effect
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.get("/dashboard/stats")

        assert res.status_code == 200
        assert res.json() == {
            "products_count": 0,
            "posts_count": 0,
            "lists_count": 0,
            "scheduled_posts": 0,
        }

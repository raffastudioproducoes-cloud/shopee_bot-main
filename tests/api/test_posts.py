"""Testes do router de posts (FastAPI). Sem mídia/thread (ver posts.py)."""

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


class TestPostsAuthRequirement:
    def test_list_requires_auth(self, client):
        res = client.get("/posts")
        assert res.status_code == 401

    def test_create_requires_auth(self, client):
        res = client.post("/posts", json={"text": "sem auth"})
        assert res.status_code == 401

    def test_get_requires_auth(self, client):
        res = client.get("/posts/9999")
        assert res.status_code == 401

    def test_update_requires_auth(self, client):
        res = client.put("/posts/9999", json={"text": "x"})
        assert res.status_code == 401

    def test_delete_requires_auth(self, client):
        res = client.delete("/posts/9999")
        assert res.status_code == 401

    def test_generate_copy_requires_auth(self, client):
        res = client.post("/posts/generate-copy", json={"product_id": 1})
        assert res.status_code == 401

    def test_publish_requires_auth(self, client):
        res = client.post("/posts/9999/publish")
        assert res.status_code == 401

    def test_upload_media_requires_auth(self, client):
        res = client.post(
            "/posts/9999/media",
            files={"file": ("foto.jpg", b"conteudo-fake", "image/jpeg")},
        )
        assert res.status_code == 401

    def test_delete_media_requires_auth(self, client):
        res = client.delete("/posts/9999/media/1")
        assert res.status_code == 401


class TestListPostsAuthenticated:
    def test_list_posts_calls_supabase_table_via_proxy(self, auth_client, monkeypatch):
        """Regression: `supabase` from api/database.py used to be a bare
        function, so `supabase.table(...)` raised AttributeError on every
        DB-touching call (see _SupabaseProxy in api/database.py)."""
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.is_.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = MagicMock(data=[])

        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.get("/posts")

        assert res.status_code == 200
        assert res.json() == {"data": [], "next_cursor": None}
        fake_client.table.assert_called_with("posts")

"""Testes do router de posts (FastAPI). Sem mídia/thread (ver posts.py)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers import posts as posts_module
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


def _mock_supabase_for_upload(monkeypatch):
    """Mock Supabase pra fluxo de upload (ownership + insert medias/posts_medias)."""
    fake_client = MagicMock()

    def table_side_effect(name):
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.single.return_value = query
        query.order.return_value = query
        query.insert.return_value = query
        if name == "posts":
            query.execute.return_value = MagicMock(data={"id": 9999, "user_id": 42})
        elif name == "medias":
            query.execute.return_value = MagicMock(
                data=[{"id": 1, "file_name": "foto.jpg", "size": 3, "type": "IMAGE"}]
            )
        else:
            query.execute.return_value = MagicMock(data=[])
        return query

    fake_client.table.side_effect = table_side_effect
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return fake_client


class TestUploadMediaContentValidation:
    """Auditoria de segurança: extensão .jpg com conteúdo não-imagem deve ser
    rejeitada por magic bytes (fleep), não só pela extensão do nome."""

    def test_rejects_jpg_extension_with_non_image_content(self, auth_client, monkeypatch, tmp_path):
        _mock_supabase_for_upload(monkeypatch)
        monkeypatch.setattr(posts_module, "MEDIA_ROOT", tmp_path)

        res = auth_client.post(
            "/posts/9999/media",
            files={"file": ("foto.jpg", b"isso aqui e so texto puro, nao imagem", "image/jpeg")},
        )

        assert res.status_code == 400
        assert "não corresponde a uma mídia permitida" in res.json()["detail"]

    def test_accepts_jpg_with_real_jpeg_signature(self, auth_client, monkeypatch, tmp_path):
        _mock_supabase_for_upload(monkeypatch)
        monkeypatch.setattr(posts_module, "MEDIA_ROOT", tmp_path)

        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 32

        res = auth_client.post(
            "/posts/9999/media",
            files={"file": ("foto.jpg", jpeg_bytes, "image/jpeg")},
        )

        assert res.status_code == 201


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

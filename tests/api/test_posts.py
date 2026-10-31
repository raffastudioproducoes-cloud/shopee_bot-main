"""Testes do router de posts (FastAPI). Sem mídia/thread (ver posts.py)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Cliente autenticado (user_id=42) com Supabase mockado."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
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
    fake_client.rpc.return_value.execute.return_value = MagicMock(data={
        "allowed": True, "reservation_id": "22222222-2222-4222-8222-222222222222",
    })
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return fake_client


def _real_jpeg() -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buf, format="JPEG")
    return buf.getvalue()


class TestUploadMediaContentValidation:
    """Auditoria de segurança: extensão .jpg com conteúdo não-imagem deve ser
    rejeitada pelo conteúdo real (magic bytes), não só pela extensão do nome."""

    def test_rejects_jpg_extension_with_non_image_content(self, auth_client, monkeypatch):
        fake = _mock_supabase_for_upload(monkeypatch)

        res = auth_client.post(
            "/posts/9999/media",
            files={"file": ("foto.jpg", b"isso aqui e so texto puro, nao imagem", "image/jpeg")},
        )

        assert res.status_code == 415
        assert "Arquivo inválido ou não suportado" in res.json()["detail"]
        fake.storage.from_.return_value.upload.assert_not_called()

    def test_accepts_jpg_with_real_jpeg_and_stores_in_private_bucket(self, auth_client, monkeypatch):
        fake = _mock_supabase_for_upload(monkeypatch)

        res = auth_client.post(
            "/posts/9999/media",
            files={"file": ("foto.jpg", _real_jpeg(), "image/jpeg")},
        )

        assert res.status_code == 201
        fake.storage.from_.assert_called_with("post-media")
        fake.storage.from_.return_value.upload.assert_called_once()


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

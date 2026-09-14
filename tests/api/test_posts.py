"""Testes do router de posts (FastAPI). Sem mídia/thread (ver posts.py)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
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

"""Testes do router de usuários (FastAPI). Admin-only — ver _require_admin."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


class TestUsersAuthRequirement:
    """Sem sessão, 401 vem antes do gate de admin (403)."""

    def test_list_requires_auth(self, client):
        res = client.get("/users")
        assert res.status_code == 401

    def test_create_requires_auth(self, client):
        res = client.post(
            "/users",
            json={"username": "novo", "password": "senha123", "access": "USER"},
        )
        assert res.status_code == 401

    def test_get_requires_auth(self, client):
        res = client.get("/users/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 401

    def test_update_requires_auth(self, client):
        res = client.put(
            "/users/00000000-0000-0000-0000-000000000000",
            json={"username": "x", "access": "USER"},
        )
        assert res.status_code == 401

    def test_delete_requires_auth(self, client):
        res = client.delete("/users/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 401

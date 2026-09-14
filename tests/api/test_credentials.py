"""Testes do router de credenciais (FastAPI). Nunca deve devolver segredo."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


class TestCredentialsAuthRequirement:
    def test_list_requires_auth(self, client):
        res = client.get("/credentials")
        assert res.status_code == 401

    def test_save_simple_network_requires_auth(self, client):
        res = client.put(
            "/credentials/x", json={"app_id": "a", "secret": "s"}
        )
        assert res.status_code == 401

    def test_delete_simple_network_requires_auth(self, client):
        res = client.delete("/credentials/x")
        assert res.status_code == 401

    def test_save_threads_requires_auth(self, client):
        res = client.put(
            "/credentials/threads",
            json={"t_user_id": "1", "access_token": "tok"},
        )
        assert res.status_code == 401

    def test_delete_threads_requires_auth(self, client):
        res = client.delete("/credentials/threads")
        assert res.status_code == 401


class TestCredentialsUnknownNetwork:
    def test_unknown_network_requires_auth_first(self, client):
        # sem sessão, 401 vem antes de validar a rede — comportamento
        # correto (nunca revela quais redes existem pra quem não logou)
        res = client.put(
            "/credentials/rede-que-nao-existe",
            json={"app_id": "a", "secret": "s"},
        )
        assert res.status_code == 401

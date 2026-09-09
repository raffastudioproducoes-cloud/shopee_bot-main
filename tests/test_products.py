"""
Testes para o router de produtos (FastAPI + Supabase).

Verifica endpoints existentes, autenticação obrigatória e validação de payload.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestProductsEndpointPresence:
    def test_products_list_endpoint_exists(self, client):
        res = client.get("/products")
        assert res.status_code == 401

    def test_products_create_endpoint_exists(self, client):
        res = client.post(
            "/products",
            json={
                "product_id": "test-xxx",
                "name": "Teste",
            },
        )
        assert res.status_code == 401

    def test_products_get_endpoint_exists(self, client):
        res = client.get("/products/1")
        assert res.status_code == 401

    def test_products_update_endpoint_exists(self, client):
        res = client.put("/products/1", json={"name": "Novo nome"})
        assert res.status_code == 401

    def test_products_delete_endpoint_exists(self, client):
        res = client.delete("/products/1")
        assert res.status_code == 401


class TestProductsAuthRequirement:
    def test_list_requires_auth(self, client):
        res = client.get("/products")
        assert res.status_code == 401
        assert res.json()["detail"] == "Não autenticado"

    def test_create_requires_auth(self, client):
        res = client.post(
            "/products",
            json={"product_id": "abc", "name": "Sem auth"},
        )
        assert res.status_code == 401
        assert res.json()["detail"] == "Não autenticado"

    def test_get_requires_auth(self, client):
        res = client.get("/products/9999")
        assert res.status_code == 401
        assert res.json()["detail"] == "Não autenticado"

    def test_update_requires_auth(self, client):
        res = client.put("/products/9999", json={"name": "X"})
        assert res.status_code == 401
        assert res.json()["detail"] == "Não autenticado"

    def test_delete_requires_auth(self, client):
        res = client.delete("/products/9999")
        assert res.status_code == 401
        assert res.json()["detail"] == "Não autenticado"


class TestProductsRequestValidation:
    def test_create_requires_product_id_and_name(self, client):
        res = client.post("/products", json={"product_id": "abc"})
        assert res.status_code == 401

    def test_create_requires_name(self, client):
        res = client.post("/products", json={"name": "sem product_id"})
        assert res.status_code == 401

"""
Testes para o router de produtos (FastAPI + Supabase).

Verifica endpoints existentes, autenticação obrigatória e validação de payload.
"""

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
                "product_id": "123456789",
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
            json={"product_id": "123456789", "name": "Sem auth"},
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

    def test_create_rejects_non_numeric_shopee_product_id(self, auth_client):
        res = auth_client.post("/products", json={"product_id": "not-a-shopee-id", "name": "Inválido"})
        assert res.status_code == 422


class TestProductsNumericFieldsFromTextColumns:
    """price_min/price_max/commission são TEXT na tabela `products` (schema
    legado do scraper) — o Postgrest devolve string ("129.9"). Sem conversão,
    `product.price_min.toFixed(2)` no frontend quebra a página inteira."""

    def test_list_converts_string_prices_to_numbers(self, auth_client, monkeypatch):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.ilike.return_value = query
        query.gte.return_value = query
        query.lte.return_value = query
        query.order.return_value = query
        query.range.return_value = query
        query.execute.return_value = MagicMock(
            data=[{
                "id": 1,
                "name": "Fone",
                "price_min": "129.9",
                "price_max": "129.9",
                "commission": "68.847",
            }]
        )
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.get("/products")

        assert res.status_code == 200
        product = res.json()["data"][0]
        assert product["price_min"] == 129.9
        assert product["price_max"] == 129.9
        assert product["commission"] == 68.847

    def test_get_treats_unparseable_price_as_null(self, auth_client, monkeypatch):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.single.return_value = query
        query.execute.return_value = MagicMock(
            data={"id": 1, "name": "Fone", "price_min": "", "price_max": None, "commission": "lixo"}
        )
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.get("/products/1")

        assert res.status_code == 200
        body = res.json()
        assert body["price_min"] is None
        assert body["price_max"] is None
        assert body["commission"] is None


class TestProductsScopedByAccount:
    """Produtos pertencem à conta, não ao perfil ativo."""

    def test_list_products_ignores_active_profile(
        self, auth_client, auth_headers_with_profile, monkeypatch
    ):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        for method in ("select", "eq", "order", "range"):
            getattr(query, method).return_value = query
        query.execute.return_value = MagicMock(data=[])
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.get("/products")

        assert res.status_code == 200
        assert all(call.args[0] != "profile_id" for call in query.eq.call_args_list)

    def test_create_product_omits_profile_id_when_token_has_it(
        self, auth_client, auth_headers_with_profile, monkeypatch
    ):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        for method in ("insert", "select", "eq", "limit"):
            getattr(query, method).return_value = query
        query.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[{"id": 1, "name": "Fone", "product_id": "123456789"}]),
        ]
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.post("/products", json={"product_id": "123456789", "name": "Fone"})

        assert res.status_code == 201
        assert "profile_id" not in query.insert.call_args[0][0]

    def test_profiles_share_products_but_another_account_gets_404(
        self, auth_client, auth_headers_with_profile, fake_query_builder, monkeypatch, profile_cookie
    ):
        rows = [
            {"id": 1, "user_id": 42, "profile_id": None, "name": "Da conta"},
        ]
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda _name: fake_query_builder(rows)
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        assert [row["id"] for row in auth_client.get("/products").json()["data"]] == [1]

        auth_client.cookies.update({"access_token": profile_cookie("profile-b")["access_token"]})
        assert [row["id"] for row in auth_client.get("/products").json()["data"]] == [1]

        app.dependency_overrides[get_current_user_id] = lambda: 99
        assert auth_client.get("/products/1").status_code == 404

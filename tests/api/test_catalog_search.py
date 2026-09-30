"""
Testes para o router de catálogo Shopee (Pesquisa Avançada).

Cobre: autenticação obrigatória, credencial Shopee ausente, fallback de
campos best-effort (schema desconhecido -> conjunto mínimo), sort_type
inválido e mapeamento da resposta.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api import shopee_catalog
from api.crypto import encrypt
from api.main import app
from api.routers.auth import get_current_user_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


@pytest.fixture
def auth_client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


def _fake_supabase_with_credential(app_id: str = "app-123", secret_plain: str = "s3cr3t"):
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(
        data={"app_id": app_id, "secret": encrypt(secret_plain)}
    )
    return fake_client


def _fake_supabase_without_credential():
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data=None)
    return fake_client


class TestCatalogEndpointsAuthRequirement:
    def test_catalog_search_requires_auth(self, client):
        res = client.get("/products/catalog-search")
        assert res.status_code == 401

    def test_catalog_categories_requires_auth(self, client):
        res = client.get("/products/catalog-categories")
        assert res.status_code == 401


class TestCatalogSearchCredential:
    def test_search_without_shopee_credential_returns_clear_error(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_without_credential()
        )
        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 400
        assert "credencial" in res.json()["detail"].lower()

    def test_search_with_invalid_sort_type_is_rejected(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )
        res = auth_client.get("/products/catalog-search", params={"sort_type": 99})
        assert res.status_code == 400
        assert "sort_type" in res.json()["detail"]

    def test_search_limit_above_max_is_rejected(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )
        res = auth_client.get("/products/catalog-search", params={"limit": 9999})
        assert res.status_code == 422


class TestCatalogSearchFieldFallback:
    def test_search_falls_back_to_minimal_fields_on_unknown_field_error(
        self, auth_client, monkeypatch
    ):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        rich_error = {
            "errors": [{"message": "Cannot query field \"sales\" on type \"ProductOfferV2\"."}],
        }
        minimal_success = {
            "data": {
                "productOfferV2": {
                    "nodes": [{
                        "itemId": "111",
                        "offerLink": "https://s.shopee.com.br/offer",
                        "productName": "Fone Bluetooth",
                        "productLink": "https://shopee.com.br/prod-111",
                        "imageUrl": "https://img/1.jpg",
                        "priceMax": "129.90",
                        "priceMin": "99.90",
                        "commission": "12.5",
                    }]
                }
            }
        }

        responses = [rich_error, minimal_success]

        class FakeResponse:
            def __init__(self, body):
                self.status_code = 200
                self._body = body

            def json(self):
                return self._body

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse(responses.pop(0))

        monkeypatch.setattr(
            "httpx.AsyncClient.post", fake_post
        )

        res = auth_client.get("/products/catalog-search", params={"keyword": "fone"})

        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        product = data[0]
        assert product["product_id"] == "111"
        assert product["name"] == "Fone Bluetooth"
        assert product["original_link"] == "https://shopee.com.br/prod-111"
        assert product["commission_link"] == "https://s.shopee.com.br/offer"
        assert product["image"] == "https://img/1.jpg"
        assert product["price_min"] == "99.90"
        assert product["price_max"] == "129.90"
        assert product["commission"] == "12.5"
        # Campos best-effort ausentes no fallback mínimo -> None, sem quebrar.
        assert product["sales"] is None
        assert product["rating_star"] is None
        assert product["shop_name"] is None
        assert product["commission_rate"] is None
        # Confirma que o fallback realmente foi exercitado (2 chamadas).
        assert responses == []

    def test_search_does_not_fallback_on_unrelated_graphql_error(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"errors": [{"message": "Internal server error"}]}

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 502

    def test_search_maps_rich_fields_when_shopee_accepts_them(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        class FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "data": {
                        "productOfferV2": {
                            "nodes": [{
                                "itemId": "222",
                                "offerLink": "https://s.shopee.com.br/offer2",
                                "productName": "Mouse Gamer",
                                "productLink": "https://shopee.com.br/prod-222",
                                "imageUrl": "https://img/2.jpg",
                                "priceMax": "89.90",
                                "priceMin": "79.90",
                                "commission": "9.0",
                                "sales": 1500,
                                "ratingStar": 4.8,
                                "shopName": "Loja XYZ",
                                "commissionRate": "0.1",
                            }]
                        }
                    }
                }

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 200
        product = res.json()["data"][0]
        assert product["sales"] == 1500
        assert product["rating_star"] == 4.8
        assert product["shop_name"] == "Loja XYZ"
        assert product["commission_rate"] == "0.1"

    def test_search_auth_error_returns_422(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        class FakeResponse:
            status_code = 401

            def json(self):
                return {}

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 422


class TestCatalogCategories:
    def test_categories_returns_flattened_list(self, auth_client, monkeypatch):
        async def fake_get_category_list():
            return [
                {"name": "Moda Feminina", "category_id": 1, "parent_id": None},
                {"name": "Vestidos", "category_id": 2, "parent_id": 1},
            ]

        monkeypatch.setattr(shopee_catalog, "get_category_list", fake_get_category_list)

        res = auth_client.get("/products/catalog-categories")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data[0]["category_id"] == 1
        assert data[1]["parent_id"] == 1

    def test_categories_failure_returns_502(self, auth_client, monkeypatch):
        async def fake_get_category_list():
            raise shopee_catalog.ShopeeCatalogError("boom")

        monkeypatch.setattr(shopee_catalog, "get_category_list", fake_get_category_list)

        res = auth_client.get("/products/catalog-categories")
        assert res.status_code == 502

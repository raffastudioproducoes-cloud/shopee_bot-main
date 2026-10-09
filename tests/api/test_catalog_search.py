"""
Testes para o router de catálogo Shopee (Pesquisa Avançada).

Cobre: autenticação obrigatória, credencial Shopee ausente, fallback de
campos best-effort (schema desconhecido -> conjunto mínimo), sort_type
inválido e mapeamento da resposta.
"""

import json
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
        assert product["commission"] == 9.62  # 12.5 / 129.90, em %
        assert product["commission_amount"] == 12.5
        # Campos best-effort ausentes no fallback mínimo -> None, sem quebrar.
        assert product["sales"] is None
        assert product["rating_star"] is None
        assert product["shop_name"] is None
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
        assert product["commission"] == 10.0

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


class TestCatalogSearchInjectionAndRateLimit:
    """Regressão dos achados MEDIUM-1 (injeção via `keyword`) e MEDIUM-2
    (rate limit) da revisão de segurança."""

    def test_keyword_with_escaped_quote_does_not_break_query_or_inject(
        self, auth_client, monkeypatch
    ):
        """Reproduz o caso do reviewer: keyword terminando em `\\"` (barra
        invertida + aspas) — com concatenação de string isso fechava a
        string antes do esperado e permitia injetar campos/queries
        arbitrários. Com variáveis GraphQL, o valor nunca é interpolado na
        string da query, então a busca deve simplesmente funcionar."""
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        malicious_keyword = (
            'x\\") { itemId } } conversionReport { nodes { purchaseTime } } '
            'a: productOfferV2(keyword: "y'
        )

        captured = {}

        class FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "data": {"productOfferV2": {"nodes": []}}
                }

        async def fake_post(self, url, content=None, headers=None):
            captured["payload"] = json.loads(content)
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        res = auth_client.get(
            "/products/catalog-search", params={"keyword": malicious_keyword}
        )

        assert res.status_code == 200
        assert res.json()["data"] == []

        # O valor malicioso foi enviado só como variável, nunca interpolado
        # na string da query — a query em si não contém o payload injetado.
        sent = captured["payload"]
        assert sent["variables"]["kw"] == malicious_keyword
        assert "conversionReport" not in sent["query"]
        assert malicious_keyword not in sent["query"]
        assert "$kw" in sent["query"]

    def test_keyword_longer_than_max_length_is_rejected(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )
        res = auth_client.get(
            "/products/catalog-search", params={"keyword": "a" * 201}
        )
        assert res.status_code == 422

    def test_search_rate_limit_blocks_after_threshold(self, auth_client, monkeypatch):
        from api.routers import catalog as catalog_router

        catalog_router._search_attempts.clear()
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"data": {"productOfferV2": {"nodes": []}}}

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        limit = catalog_router._SEARCH_RATE_LIMIT_ATTEMPTS
        for _ in range(limit):
            res = auth_client.get("/products/catalog-search")
            assert res.status_code == 200

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 429
        catalog_router._search_attempts.clear()


class TestCatalogSearchErrorClassification:
    """Regressão do achado LOW-1: 429/5xx da própria Shopee não deve
    virar "credencial inválida"."""

    def test_http_429_is_generic_error_not_auth_error(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        class FakeResponse:
            status_code = 429

            def json(self):
                return {}

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 502

    def test_http_500_is_generic_error_not_auth_error(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        class FakeResponse:
            status_code = 500

            def json(self):
                return {}

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 502

    def test_non_json_response_does_not_crash_with_500(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            database_module, "get_supabase", lambda: _fake_supabase_with_credential()
        )

        class FakeResponse:
            status_code = 200

            def json(self):
                raise ValueError("not json")

        async def fake_post(self, url, content=None, headers=None):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 502


class TestCatalogSearchCredentialDecryptFailure:
    """Regressão do achado LOW-2: chave de criptografia rotacionada não
    deve virar 500 cru (InvalidToken sem tratamento)."""

    def test_invalid_token_on_decrypt_returns_clear_400(self, auth_client, monkeypatch):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.maybe_single.return_value = query
        query.execute.return_value = MagicMock(
            data={"app_id": "app-123", "secret": "not-a-valid-fernet-token"}
        )
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 400
        assert "reconecte" in res.json()["detail"].lower()


class TestCatalogCategoriesLoopAndCache:
    """Regressão do achado MEDIUM-2: loop de paginação de categorias."""

    def test_empty_global_cats_before_total_reached_does_not_hang(self, monkeypatch):
        shopee_catalog._category_cache["data"] = None
        shopee_catalog._category_cache["expires_at"] = 0.0

        call_count = {"n": 0}

        async def fake_get_global_category_list(page, size=1000):
            call_count["n"] += 1
            if page == 1:
                return {
                    "total": 100,
                    "global_cats": [
                        {"path": [{"category_id": 1, "category_name": "Moda"}]},
                    ],
                }
            # Página seguinte vem vazia antes de atingir `total` — não deve
            # entrar em loop infinito, deve simplesmente parar.
            return {"total": 100, "global_cats": []}

        monkeypatch.setattr(
            shopee_catalog, "_get_global_category_list", fake_get_global_category_list
        )

        import asyncio

        result = asyncio.run(shopee_catalog.get_category_list())
        assert len(result) == 1
        assert call_count["n"] == 2

        shopee_catalog._category_cache["data"] = None
        shopee_catalog._category_cache["expires_at"] = 0.0

    def test_missing_total_and_global_cats_does_not_crash(self, monkeypatch):
        shopee_catalog._category_cache["data"] = None
        shopee_catalog._category_cache["expires_at"] = 0.0

        async def fake_get_global_category_list(page, size=1000):
            return {}  # sem 'total' nem 'global_cats'

        monkeypatch.setattr(
            shopee_catalog, "_get_global_category_list", fake_get_global_category_list
        )

        import asyncio

        result = asyncio.run(shopee_catalog.get_category_list())
        assert result == []

        shopee_catalog._category_cache["data"] = None
        shopee_catalog._category_cache["expires_at"] = 0.0

    def test_result_is_cached_between_calls(self, monkeypatch):
        shopee_catalog._category_cache["data"] = None
        shopee_catalog._category_cache["expires_at"] = 0.0

        call_count = {"n": 0}

        async def fake_get_global_category_list(page, size=1000):
            call_count["n"] += 1
            return {
                "total": 1,
                "global_cats": [
                    {"path": [{"category_id": 1, "category_name": "Moda"}]},
                ],
            }

        monkeypatch.setattr(
            shopee_catalog, "_get_global_category_list", fake_get_global_category_list
        )

        import asyncio

        first = asyncio.run(shopee_catalog.get_category_list())
        second = asyncio.run(shopee_catalog.get_category_list())

        assert first == second
        assert call_count["n"] == 1  # segunda chamada veio do cache

        shopee_catalog._category_cache["data"] = None
        shopee_catalog._category_cache["expires_at"] = 0.0


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


class _Resp:
    def __init__(self, body, status_code=200):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def _nodes(n, start=0):
    return [{"itemId": str(start + i), "productName": f"P{start + i}"} for i in range(n)]


def _capture_posts(monkeypatch, bodies):
    sent = []

    async def fake_post(self, url, content=None, headers=None):
        sent.append(json.loads(content))
        return _Resp(bodies.pop(0) if bodies else {"data": {"productOfferV2": {"nodes": []}}})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    return sent


def _post_returning(monkeypatch, body, status_code=200):
    async def fake_post(self, url, content=None, headers=None):
        return _Resp(body, status_code)

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)


@pytest.fixture
def with_credential(monkeypatch):
    from api.routers import catalog as catalog_router

    catalog_router._search_attempts.clear()
    monkeypatch.setattr(
        database_module, "get_supabase",
        lambda: _fake_supabase_with_credential(secret_plain="SUPERSECRET"),
    )
    yield
    catalog_router._search_attempts.clear()


class TestCatalogSearchQueryTypes:
    """Regressão do 502 em produção: `$cat: Int64` declarado contra
    `productCatId: Int32` no schema da Shopee invalidava a query inteira."""

    def test_query_without_category_has_no_int64_or_productcatid(
        self, auth_client, monkeypatch, with_credential
    ):
        sent = _capture_posts(monkeypatch, [])
        res = auth_client.get("/products/catalog-search", params={"keyword": "sapato", "sort_type": 1})
        assert res.status_code == 200
        q = sent[0]["query"]
        assert "Int64" not in q
        assert "productCatId" not in q
        assert "sortType: 1" in q
        assert sent[0]["variables"] == {"kw": "sapato"}

    def test_category_goes_as_integer_literal(self, auth_client, monkeypatch, with_credential):
        sent = _capture_posts(monkeypatch, [])
        res = auth_client.get(
            "/products/catalog-search", params={"product_cat_id": 100636, "sort_type": 2},
        )
        assert res.status_code == 200
        q = sent[0]["query"]
        assert "productCatId: 100636" in q
        assert "sortType: 2" in q
        assert "$cat" not in q and "Int64" not in q
        assert "$kw" not in q

    def test_category_out_of_int32_range_is_rejected(self, auth_client, with_credential):
        res = auth_client.get("/products/catalog-search", params={"product_cat_id": 2**31})
        assert res.status_code == 422


class TestCatalogSearchPagination:
    def test_limit_150_is_split_in_pages_of_50(self, auth_client, monkeypatch, with_credential):
        bodies = [
            {"data": {"productOfferV2": {"nodes": _nodes(50, 0)}}},
            {"data": {"productOfferV2": {"nodes": _nodes(50, 50)}}},
            {"data": {"productOfferV2": {"nodes": _nodes(50, 100)}}},
        ]
        sent = _capture_posts(monkeypatch, bodies)
        res = auth_client.get("/products/catalog-search", params={"keyword": "x", "limit": 150})
        assert res.status_code == 200
        assert len(res.json()["data"]) == 150
        assert len(sent) == 3
        for i, payload in enumerate(sent, start=1):
            assert f"page: {i}" in payload["query"]
            assert "limit: 50" in payload["query"]

    def test_stops_when_page_is_short(self, auth_client, monkeypatch, with_credential):
        sent = _capture_posts(monkeypatch, [{"data": {"productOfferV2": {"nodes": _nodes(7)}}}])
        res = auth_client.get("/products/catalog-search", params={"limit": 150})
        assert res.status_code == 200
        assert len(res.json()["data"]) == 7
        assert len(sent) == 1

    def test_default_limit_is_50_single_call(self, auth_client, monkeypatch, with_credential):
        sent = _capture_posts(monkeypatch, [])
        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 200
        assert "limit: 50" in sent[0]["query"] and "page: 1" in sent[0]["query"]


class TestCatalogSearchSpecificErrors:
    def test_signature_error_code_10020_asks_to_reconnect(self, auth_client, monkeypatch, with_credential):
        _post_returning(monkeypatch, {"errors": [
            {"message": "Invalid Signature", "extensions": {"code": 10020, "message": "Invalid Signature"}},
        ]})
        res = auth_client.get("/products/catalog-search", params={"keyword": "sapato"})
        assert res.status_code == 422
        assert "Credenciais" in res.json()["detail"]

    def test_http_401_asks_to_reconnect(self, auth_client, monkeypatch, with_credential):
        _post_returning(monkeypatch, {}, status_code=401)
        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 422
        assert "Reconecte" in res.json()["detail"]

    def test_rate_limit_code_10030_has_specific_message(self, auth_client, monkeypatch, with_credential):
        _post_returning(monkeypatch, {"errors": [
            {"message": "Rate limit exceeded", "extensions": {"code": 10030}},
        ]})
        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 502
        assert "limitou" in res.json()["detail"]

    def test_schema_validation_error_is_logged_without_secret(
        self, auth_client, monkeypatch, caplog, with_credential
    ):
        _post_returning(monkeypatch, {"errors": [
            {"message": 'Variable "$cat" of type "Int64" used in position expecting type "Int32".'},
        ]})
        with caplog.at_level("WARNING", logger="api.routers.catalog"):
            res = auth_client.get("/products/catalog-search")
        assert res.status_code == 502
        assert "recusou" in res.json()["detail"]
        assert "Int32" in caplog.text
        assert "SUPERSECRET" not in caplog.text

    def test_network_failure_says_shopee_unavailable(self, auth_client, monkeypatch, with_credential):
        import httpx

        async def boom(self, url, content=None, headers=None):
            raise httpx.ConnectError("down")

        monkeypatch.setattr("httpx.AsyncClient.post", boom)
        res = auth_client.get("/products/catalog-search")
        assert res.status_code == 502
        assert "indisponível" in res.json()["detail"]

    def test_no_results_returns_empty_list(self, auth_client, monkeypatch, with_credential):
        _post_returning(monkeypatch, {"data": {"productOfferV2": {"nodes": None}}})
        res = auth_client.get("/products/catalog-search", params={"keyword": "zzz"})
        assert res.status_code == 200
        assert res.json()["data"] == []

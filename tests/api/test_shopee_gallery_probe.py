"""F2: contrato read-only da galeria Shopee, com GraphQL simulado.

Nunca usa credencial real, mídia de usuário, rede externa ou postagem.
"""
import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import shopee_catalog
from api.main import app
from api.routers import catalog
from api.routers.auth import get_current_user_id


def run(coro):
    return asyncio.run(coro)


def test_probe_reports_multiple_only_when_official_response_has_urls(monkeypatch):
    requests = []

    async def fake_graphql(_app_id, _secret, query, _variables):
        requests.append(query)
        return {"productOfferV2": {"nodes": [{
            "itemId": "123", "imageUrl": "https://img.susercontent.com/main.jpg",
            "imageUrls": [
                "https://img.susercontent.com/main.jpg",
                "https://img.susercontent.com/two.jpg",
                "https://img.susercontent.com/three.jpg",
            ],
        }]}}

    monkeypatch.setattr(shopee_catalog, "_post_graphql", fake_graphql)
    result = run(shopee_catalog.probe_product_gallery("app", "secret", item_id=123))
    assert result["status"] == "multiple"
    assert len(result["image_urls"]) == 3
    assert len(requests) == 1
    assert "productOfferV2(itemId: 123)" in requests[0]
    assert "imageUrls" in requests[0]


def test_probe_falls_back_to_existing_main_image_when_schema_rejects_candidate(monkeypatch):
    requests = []

    async def fake_graphql(_app_id, _secret, query, _variables):
        requests.append(query)
        if "imageUrls" in query:
            raise shopee_catalog.ShopeeCatalogError(
                "Campo ausente",
                errors=[{"message": 'Cannot query field "imageUrls" on type "ProductOfferV2".'}],
            )
        return {"productOfferV2": {"nodes": [{
            "itemId": 123, "imageUrl": "https://img.susercontent.com/main.jpg",
        }]}}

    monkeypatch.setattr(shopee_catalog, "_post_graphql", fake_graphql)
    result = run(shopee_catalog.probe_product_gallery("app", "secret", item_id=123))
    assert result["status"] == "field_unavailable"
    assert result["image_urls"] == ["https://img.susercontent.com/main.jpg"]
    assert len(requests) == 2
    assert "imageUrls" not in requests[1]


def test_probe_does_not_swallow_auth_or_rate_limit_errors(monkeypatch):
    async def fake_graphql(*_args, **_kwargs):
        raise shopee_catalog.ShopeeRateLimitError("429")

    monkeypatch.setattr(shopee_catalog, "_post_graphql", fake_graphql)
    with pytest.raises(shopee_catalog.ShopeeRateLimitError):
        run(shopee_catalog.probe_product_gallery("app", "secret", item_id=123))


def test_probe_rejects_unbounded_item_id_before_network_call():
    with pytest.raises(ValueError):
        run(shopee_catalog.probe_product_gallery("app", "secret", item_id=-1))


def _client(monkeypatch, row):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    fake_db = MagicMock()
    query = fake_db.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data=row)
    monkeypatch.setattr(catalog, "supabase", fake_db)
    monkeypatch.setattr(catalog, "_check_search_rate_limit", lambda _user: None)
    monkeypatch.setattr(catalog, "_get_shopee_credential", lambda _user: ("app", "secret"))
    return TestClient(app), fake_db


def test_gallery_endpoint_uses_account_scope_and_excludes_untrusted_hosts(monkeypatch):
    client, db = _client(monkeypatch, {
        "id": 10, "product_id": "123",
        "image": "https://img.susercontent.com/main.jpg",
    })

    async def fake_probe(*_args, **_kwargs):
        return {
            "image_urls": [
                "https://img.susercontent.com/extra.jpg",
                "https://evil.example.org/ssrf",
                "http://img.susercontent.com/insecure.jpg",
            ],
            "status": "multiple", "field_tested": "imageUrls",
        }

    monkeypatch.setattr(shopee_catalog, "probe_product_gallery", fake_probe)
    response = client.get("/products/10/shopee-gallery-probe")
    assert response.status_code == 200
    assert response.json()["status"] == "multiple"
    assert response.json()["image_urls"] == [
        "https://img.susercontent.com/extra.jpg",
        "https://img.susercontent.com/main.jpg",
    ]
    assert any(x.args == ("user_id", 42) for x in db.table.return_value.eq.call_args_list)
    assert db.table.call_args.args[0] == "products"
    app.dependency_overrides.clear()


def test_gallery_endpoint_returns_stored_main_photo_if_shopee_unavailable(monkeypatch):
    client, _db = _client(monkeypatch, {
        "id": 10, "product_id": "123", "image": "https://img.susercontent.com/main.jpg",
    })

    async def no_shopee(*_args, **_kwargs):
        raise shopee_catalog.ShopeeCatalogError("network down")

    monkeypatch.setattr(shopee_catalog, "probe_product_gallery", no_shopee)
    response = client.get("/products/10/shopee-gallery-probe")
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["image_urls"] == ["https://img.susercontent.com/main.jpg"]
    app.dependency_overrides.clear()


def test_gallery_probe_requires_authenticated_user():
    app.dependency_overrides.clear()
    response = TestClient(app).get("/products/10/shopee-gallery-probe")
    assert response.status_code == 401

"""
Regressão: "Adicionar aos meus produtos" (Pesquisa Avançada) dava 422 e o
frontend mostrava "[object Object]".

Causa: `itemId` da Shopee é Int64 (número no JSON) e `ProductCreate.product_id`
era `str` estrito do Pydantic v2 -> 422 "Input should be a valid string".
Semântica de `products.commission`: TAXA de comissão em % (6 = 6%), igual ao
que os textos de publicação já imprimem ("Comissão: {commission}%").
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers.auth import get_current_user_id
from api.routers.catalog import _map_catalog_node


@pytest.fixture
def auth_client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fake_insert_client():
    fake_client = MagicMock()
    query = fake_client.table.return_value
    for method in ("insert", "select", "eq", "is_", "limit"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [
        MagicMock(data=[]),  # lookup de duplicidade
        MagicMock(data=[{"id": 1, "name": "Caixinha", "product_id": "23456789012"}]),
    ]
    return fake_client, query


CATALOG_PAYLOAD = {
    "product_id": 23456789012,  # Int64 como a Shopee devolve
    "name": "H'Maston H007 Caixinha De Som Bluetooth",
    "original_link": "https://shopee.com.br/product/1/23456789012",
    "commission_link": "https://s.shopee.com.br/abc",
    "commission": 6.0001,
    "image": "https://img/1.jpg",
    "price_min": 49.99,
    "price_max": 49.99,
}


def test_create_accepts_numeric_product_id_from_catalog(auth_client, monkeypatch):
    fake_client, query = _fake_insert_client()
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    res = auth_client.post("/products", json=CATALOG_PAYLOAD)

    assert res.status_code == 201, res.json()
    inserted = query.insert.call_args[0][0]
    assert inserted["product_id"] == "23456789012"
    assert inserted["user_id"] == 42


def test_create_rounds_commission_and_prices_to_two_decimals(auth_client, monkeypatch):
    fake_client, query = _fake_insert_client()
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    res = auth_client.post("/products", json={**CATALOG_PAYLOAD, "commission": 2.9994, "price_min": 49.999})

    assert res.status_code == 201
    inserted = query.insert.call_args[0][0]
    assert inserted["commission"] == 3.0
    assert inserted["price_min"] == 50.0


def test_validation_error_keeps_fastapi_list_format(auth_client):
    """O frontend normaliza `detail` lista (loc/msg) — garante o formato."""
    res = auth_client.post("/products", json={"product_id": "1"})
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["body", "name"]
    assert "msg" in detail[0]


def test_catalog_maps_rate_to_percent_and_amount_to_reais():
    node = {
        "itemId": 23456789012, "productName": "Caixinha", "priceMin": "49.99", "priceMax": "49.99",
        "commission": "2.9994", "commissionRate": "0.06",
    }
    mapped = _map_catalog_node(node)
    assert mapped["product_id"] == "23456789012"
    assert mapped["commission"] == 6.0  # taxa em %
    assert mapped["commission_amount"] == 3.0  # R$ por venda
    assert "commission_rate" not in mapped


def test_catalog_derives_rate_from_amount_when_rate_missing():
    node = {"itemId": "111", "priceMin": "99.90", "priceMax": "129.90", "commission": "12.99"}
    mapped = _map_catalog_node(node)
    assert mapped["commission"] == 10.0  # 12.99 / 129.90
    assert mapped["commission_amount"] == 12.99


def test_catalog_without_commission_data_is_none():
    mapped = _map_catalog_node({"itemId": "1", "priceMin": None, "commission": None})
    assert mapped["commission"] is None
    assert mapped["commission_amount"] is None

"""
Testes para o router de listas de produtos (FastAPI + Supabase).

Cobre a sincronização de produtos numa lista via PUT /lists/{id}
(product_ids), incluindo o caso "omitido não altera associação".
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.auth import get_current_user_id
from api.routers import lists as lists_router


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


def _make_fake_supabase(tables: dict[str, MagicMock]) -> MagicMock:
    """Cria um MagicMock cujo `.table(name)` devolve o mock configurado."""
    fake_client = MagicMock()
    fake_client.table.side_effect = lambda name: tables[name]
    return fake_client


def _query_mock(execute_return) -> MagicMock:
    """Mock de query builder encadeável (select/eq/single/in_/delete/insert...)."""
    query = MagicMock()
    for method in ("select", "eq", "single", "in_", "delete", "insert", "update", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value = execute_return
    return query


class TestListsEndpointPresence:
    def test_update_requires_auth(self, client):
        res = client.put("/lists/1", json={"name": "X"})
        assert res.status_code == 401


class TestListProductsSync:
    def test_put_with_new_product_ids_associates_products(self, auth_client, monkeypatch):
        product_lists_query = _query_mock(MagicMock(data={"id": 1, "name": "Nova", "updated_at": None}))
        products_query = _query_mock(MagicMock(data=[{"id": 10}, {"id": 20}]))
        current_assoc_query = _query_mock(MagicMock(data=[]))  # nenhum produto associado ainda
        insert_query = _query_mock(MagicMock(data=[{"product_list_id": 1, "product_id": 10}]))

        # product_lists_products é usado duas vezes (select atual + insert) —
        # troca o retorno do .table() por chamada usando um contador simples.
        calls = {"n": 0}

        def product_lists_products_table(*_args, **_kwargs):
            calls["n"] += 1
            return current_assoc_query if calls["n"] == 1 else insert_query

        fake_client = MagicMock()

        def table_side_effect(name):
            if name == "product_lists":
                return product_lists_query
            if name == "products":
                return products_query
            if name == "product_lists_products":
                return product_lists_products_table()
            raise AssertionError(f"tabela inesperada: {name}")

        fake_client.table.side_effect = table_side_effect
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        res = auth_client.put("/lists/1", json={"name": "Nova", "product_ids": [10, 20]})

        assert res.status_code == 200
        insert_query.insert.assert_called_once()
        inserted_rows = insert_query.insert.call_args[0][0]
        assert {row["product_id"] for row in inserted_rows} == {10, 20}

    def test_put_removing_id_from_product_ids_disassociates(self, auth_client, monkeypatch):
        product_lists_query = _query_mock(MagicMock(data={"id": 1, "name": "Lista", "updated_at": None}))
        products_query = _query_mock(MagicMock(data=[{"id": 10}]))  # só o 10 pertence ao usuário
        current_assoc_query = _query_mock(MagicMock(data=[{"product_id": 10}, {"product_id": 20}]))
        delete_query = _query_mock(MagicMock(data=[{"product_id": 20}]))

        calls = {"n": 0}

        def product_lists_products_table(*_args, **_kwargs):
            calls["n"] += 1
            return current_assoc_query if calls["n"] == 1 else delete_query

        fake_client = MagicMock()

        def table_side_effect(name):
            if name == "product_lists":
                return product_lists_query
            if name == "products":
                return products_query
            if name == "product_lists_products":
                return product_lists_products_table()
            raise AssertionError(f"tabela inesperada: {name}")

        fake_client.table.side_effect = table_side_effect
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        # produto_ids só contém o 10 -> o 20 deve ser desassociado
        res = auth_client.put("/lists/1", json={"name": "Lista", "product_ids": [10]})

        assert res.status_code == 200
        delete_query.delete.assert_called_once()
        delete_query.in_.assert_any_call("product_id", [20])

    def test_put_without_product_ids_does_not_touch_association(self, auth_client, monkeypatch):
        product_lists_query = _query_mock(MagicMock(data={"id": 1, "name": "Renomeada", "updated_at": None}))

        fake_client = MagicMock()

        def table_side_effect(name):
            if name == "product_lists":
                return product_lists_query
            raise AssertionError(f"tabela inesperada não deveria ser tocada: {name}")

        fake_client.table.side_effect = table_side_effect
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        res = auth_client.put("/lists/1", json={"name": "Renomeada"})

        assert res.status_code == 200
        assert res.json()["name"] == "Renomeada"

    def test_put_with_empty_product_ids_removes_all_associations(self, auth_client, monkeypatch):
        product_lists_query = _query_mock(MagicMock(data={"id": 1, "name": "Lista", "updated_at": None}))
        current_assoc_query = _query_mock(MagicMock(data=[{"product_id": 10}, {"product_id": 20}]))
        delete_query = _query_mock(MagicMock(data=[]))

        calls = {"n": 0}

        def product_lists_products_table(*_args, **_kwargs):
            calls["n"] += 1
            return current_assoc_query if calls["n"] == 1 else delete_query

        fake_client = MagicMock()

        def table_side_effect(name):
            if name == "product_lists":
                return product_lists_query
            if name == "product_lists_products":
                return product_lists_products_table()
            raise AssertionError(f"tabela inesperada: {name}")

        fake_client.table.side_effect = table_side_effect
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        # product_ids=[] não deve nem consultar `products` (lista vazia = sem owned_ids)
        res = auth_client.put("/lists/1", json={"name": "Lista", "product_ids": []})

        assert res.status_code == 200
        delete_query.delete.assert_called_once()
        removed_ids = delete_query.in_.call_args[0][1]
        assert set(removed_ids) == {10, 20}

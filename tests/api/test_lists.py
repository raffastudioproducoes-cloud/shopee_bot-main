"""
Testes para o router de listas de produtos (FastAPI + Supabase).

Cobre a sincronização de produtos numa lista via PUT /lists/{id}
(product_ids), incluindo o caso "omitido não altera associação".
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
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
    for method in ("select", "eq", "single", "maybe_single", "in_", "delete", "insert", "update", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value = execute_return
    return query


class TestListsEndpointPresence:
    def test_update_requires_auth(self, client):
        res = client.put("/lists/1", json={"name": "X"})
        assert res.status_code == 401


def test_missing_list_sdk_returns_none_not_500(monkeypatch):
    query = _query_mock(None)
    query.maybe_single.return_value = query
    db = MagicMock()
    db.table.return_value = query
    monkeypatch.setattr(lists_router, "supabase", db)
    with pytest.raises(HTTPException) as error:
        lists_router._get_list(42, 7, "profile-a")
    assert error.value.status_code == 404


def test_list_product_projection_includes_saved_description(monkeypatch):
    query = _query_mock(MagicMock(data=[{"products": {
        "id": 7, "name": "Bolsa", "description": "Texto personalizado em Produtos",
    }}]))
    db = _make_fake_supabase({"product_lists_products": query})
    monkeypatch.setattr(lists_router, "supabase", db)

    products = lists_router._get_list_products(3)
    assert products[0]["description"] == "Texto personalizado em Produtos"
    select_fields = query.select.call_args.args[0]
    assert "products(id, product_id, name, description, image" in select_fields


class TestListProductsSync:
    def test_put_accepts_product_from_another_profile_of_same_account(
        self, auth_client, fake_db, profile_cookie, monkeypatch
    ):
        db = fake_db({
            "product_lists": [{"id": 1, "user_id": 42, "profile_id": "profile-a", "name": "Lista"}],
            "products": [{"id": 10, "user_id": 42, "profile_id": "profile-b"}],
            "product_lists_products": [],
        })
        monkeypatch.setattr(lists_router, "supabase", db)
        auth_client.cookies.update(profile_cookie("profile-a"))

        res = auth_client.put("/lists/1", json={"name": "Lista", "product_ids": [10]})

        assert res.status_code == 200
        assert db.tables["product_lists_products"] == [{"id": 1001, "product_list_id": 1, "product_id": 10}]

    def test_put_rejects_product_from_another_account(
        self, auth_client, fake_db, profile_cookie, monkeypatch
    ):
        db = fake_db({
            "product_lists": [{"id": 1, "user_id": 42, "profile_id": "profile-a", "name": "Lista"}],
            "products": [{"id": 10, "user_id": 99, "profile_id": "profile-x"}],
            "product_lists_products": [],
        })
        monkeypatch.setattr(lists_router, "supabase", db)
        auth_client.cookies.update(profile_cookie("profile-a"))

        res = auth_client.put("/lists/1", json={"name": "Lista", "product_ids": [10]})

        assert res.status_code == 400
        assert db.tables["product_lists_products"] == []

    def test_put_with_new_product_ids_associates_products(self, auth_client, monkeypatch):
        product_lists_query = _query_mock(MagicMock(data=[{"id": 1, "name": "Nova", "updated_at": None}]))
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
        product_lists_query = _query_mock(MagicMock(data=[{"id": 1, "name": "Lista", "updated_at": None}]))
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
        product_lists_query = _query_mock(MagicMock(data=[{"id": 1, "name": "Renomeada", "updated_at": None}]))

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
        product_lists_query = _query_mock(MagicMock(data=[{"id": 1, "name": "Lista", "updated_at": None}]))
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


class TestListsScopedByActiveProfile:
    """Task 6: listas passam a ser filtradas também por `profile_id` quando o
    token carrega essa claim; token antigo (sem `profile_id`) continua
    filtrando só por `user_id` (fallback, nunca quebra sessão existente)."""

    def test_list_product_lists_filters_by_active_profile_when_token_has_profile_id(
        self, auth_client, auth_headers_with_profile, monkeypatch
    ):
        product_lists_query = _query_mock(MagicMock(data=[]))
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda name: product_lists_query
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.get("/lists")

        assert res.status_code == 200
        product_lists_query.eq.assert_any_call("profile_id", "profile-a")

    def test_list_product_lists_does_not_filter_by_profile_when_token_has_no_profile_id(
        self, auth_client, old_token_without_profile_claim, monkeypatch
    ):
        """Token antigo (sem a claim `profile_id`) nunca deve quebrar a
        sessão existente -- exercitado com um JWT real sem essa claim, não
        apenas ausência de cookie."""
        product_lists_query = _query_mock(MagicMock(data=[]))
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda name: product_lists_query
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        auth_client.cookies.update(old_token_without_profile_claim)
        res = auth_client.get("/lists")

        assert res.status_code == 200
        for call in product_lists_query.eq.call_args_list:
            assert call.args[0] != "profile_id"

    def test_create_product_list_includes_profile_id_when_token_has_it(
        self, auth_client, auth_headers_with_profile, monkeypatch
    ):
        product_lists_query = _query_mock(
            MagicMock(data=[{"id": 1, "name": "Nova", "updated_at": None}])
        )
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda name: product_lists_query
        fake_client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"id": 1, "name": "Nova", "updated_at": None}]
        )
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.post("/lists", json={"name": "Nova"})

        assert res.status_code == 200
        assert fake_client.rpc.call_args.args[0] == "insert_product_list_with_plan_quota"
        assert fake_client.rpc.call_args.args[1]["p_profile_id"] == "profile-a"

    def test_create_product_list_without_active_profile_is_rejected(
        self, auth_client, monkeypatch
    ):
        product_lists_query = _query_mock(
            MagicMock(data=[{"id": 1, "name": "Nova", "updated_at": None}])
        )
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda name: product_lists_query
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        res = auth_client.post("/lists", json={"name": "Nova"})

        assert res.status_code == 400
        product_lists_query.insert.assert_not_called()

    def test_list_product_lists_result_actually_filtered_by_profile(
        self, auth_client, auth_headers_with_profile, fake_query_builder, monkeypatch
    ):
        """Prova que o RESULTADO muda com o filtro, não só que `.eq()` foi
        chamado: 2 listas do mesmo user_id, perfis diferentes."""
        rows = [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "name": "Da perfil A", "created_at": "2026-01-01"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "name": "Da perfil B", "created_at": "2026-01-01"},
        ]
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda _name: fake_query_builder(rows)
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.get("/lists")

        assert res.status_code == 200
        data = res.json()["data"]
        assert [row["id"] for row in data] == [1]


class TestListsByIdScopedByActiveProfile:
    """CRITICAL (fix round 1): GET/PUT/DELETE por ID vazavam entre perfis da
    mesma conta -- filtravam só por user_id. Perfil A não pode acessar
    lista do perfil B mesmo com o ID certo."""

    def _rows_with_other_profile(self):
        return [
            {"id": 7, "user_id": 42, "profile_id": "profile-b", "name": "Do perfil B", "created_at": "2026-01-01"}
        ]

    def test_get_list_from_other_profile_returns_404(
        self, auth_client, auth_headers_with_profile, fake_query_builder, monkeypatch
    ):
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda _name: fake_query_builder(self._rows_with_other_profile())
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.get("/lists/7")

        assert res.status_code == 404

    def test_update_list_from_other_profile_returns_404(
        self, auth_client, auth_headers_with_profile, fake_query_builder, monkeypatch
    ):
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda _name: fake_query_builder(self._rows_with_other_profile())
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.put("/lists/7", json={"name": "Hackeado"})

        assert res.status_code == 404

    def test_delete_list_from_other_profile_returns_404(
        self, auth_client, auth_headers_with_profile, fake_query_builder, monkeypatch
    ):
        fake_client = MagicMock()
        fake_client.table.side_effect = lambda _name: fake_query_builder(self._rows_with_other_profile())
        monkeypatch.setattr(lists_router, "supabase", fake_client)

        auth_client.cookies.update(auth_headers_with_profile)
        res = auth_client.delete("/lists/7")

        assert res.status_code == 404


def test_list_creation_returns_409_when_profile_quota_reached(
    auth_client, auth_headers_with_profile, monkeypatch
):
    fake_client = MagicMock()
    fake_client.rpc.return_value.execute.side_effect = Exception("plan_lists_quota_exceeded")
    monkeypatch.setattr(lists_router, "supabase", fake_client)
    auth_client.cookies.update(auth_headers_with_profile)
    res = auth_client.post("/lists", json={"name": "Lista excedente"})
    assert res.status_code == 409
    assert "Limite de listas" in res.json()["detail"]


def test_list_creation_denies_foreign_profile_from_rpc(
    auth_client, auth_headers_with_profile, monkeypatch
):
    fake_client = MagicMock()
    fake_client.rpc.return_value.execute.side_effect = Exception("profile_not_owned")
    monkeypatch.setattr(lists_router, "supabase", fake_client)
    auth_client.cookies.update(auth_headers_with_profile)
    res = auth_client.post("/lists", json={"name": "Lista sem dono"})
    assert res.status_code == 403

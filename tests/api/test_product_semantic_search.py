"""Contrato da busca por equivalências no catálogo da conta."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.product_search import expand_product_search, product_search_filter
from api.routers.auth import get_current_user_id


def test_lavadora_de_carro_inclui_lava_jato_e_wap():
    terms = expand_product_search("lavadora de carro")
    assert "lavadora de carro" == terms[0]
    assert "lava jato" in terms
    assert "wap" in terms
    assert "vap" in terms
    assert "hidrolavadora" in terms


def test_quarto_relaciona_produtos_de_cama_com_variantes_acentuadas():
    terms = expand_product_search("quarto")
    assert "lençol" in terms
    assert "lencol" in terms
    assert "colcha" in terms
    assert "travesseiro" in terms
    assert "guarda roupa" in terms


def test_busca_desconhecida_preserva_termo_literal():
    assert expand_product_search("Fone Bluetooth") == ["Fone Bluetooth"]


def test_saneamento_nao_permite_injecao_de_gramatica_postgrest():
    filters = product_search_filter("quarto),user_id.eq.5")
    assert filters is not None
    assert "user_id.eq" not in filters
    assert ")" not in filters
    assert "(" not in filters
    assert "name.ilike.%quarto%" in filters
    assert product_search_filter(")(,%%%") is None


@pytest.fixture
def auth_client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_busca_sempre_preserva_filtro_da_conta(auth_client, monkeypatch):
    fake_client = MagicMock()
    query = fake_client.table.return_value
    for method in ("select", "eq", "or_", "order", "range"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    response = auth_client.get("/products", params={"search": "quarto"})
    assert response.status_code == 200
    query.eq.assert_any_call("user_id", 42)
    expression = query.or_.call_args.args[0]
    assert "name.ilike.%lençol%" in expression
    assert "name.ilike.%colcha%" in expression
    assert "category.ilike.%quarto%" in expression


def test_busca_sem_termos_seguros_retorna_vazio_sem_listar_tudo(auth_client, monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    response = auth_client.get("/products", params={"search": ")(%%"})
    assert response.status_code == 200
    assert response.json()["data"] == []
    fake_client.table.return_value.execute.assert_not_called()

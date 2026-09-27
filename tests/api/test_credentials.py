"""Testes do router de credenciais (FastAPI). Nunca deve devolver segredo."""

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


def _mock_supabase(monkeypatch, execute_results):
    """Mesmo padrão de tests/api/test_users.py: mocka `supabase.table(...)`
    encadeado, devolvendo `execute_results` em ordem a cada `.execute()`."""
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.single.return_value = query
    query.maybe_single.return_value = query
    query.update.return_value = query
    query.insert.return_value = query
    query.delete.return_value = query
    query.execute.side_effect = [MagicMock(data=d) for d in execute_results]
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return query


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


class TestTestConnectionAdminGate:
    """"Testar conexão" (POST /credentials/{network}/test) é admin-only —
    a luz do sinalizador continua visível a qualquer usuário via GET
    /credentials, só o botão que dispara o teste é restrito."""

    def test_requires_auth(self, client):
        res = client.post("/credentials/shopee/test")
        assert res.status_code == 401

    def test_requires_admin(self, monkeypatch, auth_client):
        _mock_supabase(monkeypatch, [{"access": "USER"}])
        res = auth_client.post("/credentials/shopee/test")
        assert res.status_code == 403

    def test_admin_without_saved_credential_returns_400(self, monkeypatch, auth_client):
        # 1ª execute: _require_admin (access=ADMIN); 2ª: busca da credencial
        # (nenhuma linha salva) — sem credencial, nada a testar.
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None])
        res = auth_client.post("/credentials/shopee/test")
        assert res.status_code == 400

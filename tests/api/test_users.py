"""Testes do router de usuários (FastAPI). Admin-only — ver _require_admin."""

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
    """Mocka `supabase.table(...)` encadeado, devolvendo `execute_results`
    em ordem a cada `.execute()` (1ª chamada = check do _require_admin)."""
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.single.return_value = query
    query.update.return_value = query
    query.delete.return_value = query
    query.execute.side_effect = [MagicMock(data=d) for d in execute_results]
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return query


class TestUsersAuthRequirement:
    """Sem sessão, 401 vem antes do gate de admin (403)."""

    def test_list_requires_auth(self, client):
        res = client.get("/users")
        assert res.status_code == 401

    def test_create_requires_auth(self, client):
        res = client.post(
            "/users",
            json={"username": "novo", "password": "senha123", "access": "USER"},
        )
        assert res.status_code == 401

    def test_get_requires_auth(self, client):
        res = client.get("/users/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 401

    def test_update_requires_auth(self, client):
        res = client.put(
            "/users/00000000-0000-0000-0000-000000000000",
            json={"username": "x", "access": "USER"},
        )
        assert res.status_code == 401

    def test_delete_requires_auth(self, client):
        res = client.delete("/users/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 401


class TestCreateUserBlocksMasterAdminUsernameSquatting:
    """Ninguém pode criar um usuário com variante de caixa de "rafastudio"."""

    @pytest.mark.parametrize("username", ["RafaStudio", "RAFASTUDIO", "rafastudio"])
    def test_creating_user_with_master_admin_username_variant_returns_409(
        self, auth_client, monkeypatch, username
    ):
        query = _mock_supabase(monkeypatch, [{"access": "ADMIN"}])

        res = auth_client.post(
            "/users",
            json={"username": username, "password": "senha123", "access": "USER"},
        )

        assert res.status_code == 409
        query.insert.assert_not_called()


class TestUpdateUserProtectsMasterAdmin:
    """rafastudio (master admin) nunca pode ser rebaixado nem renomeado."""

    def test_downgrading_master_admin_access_is_blocked(self, auth_client, monkeypatch):
        query = _mock_supabase(
            monkeypatch,
            [
                {"access": "ADMIN"},  # _require_admin (user 42)
                {"username": "rafastudio", "access": "ADMIN"},  # fetch do alvo
            ],
        )

        res = auth_client.put("/users/1", json={"username": "rafastudio", "access": "USER"})

        assert res.status_code == 403
        query.update.assert_not_called()

    def test_renaming_master_admin_is_blocked(self, auth_client, monkeypatch):
        query = _mock_supabase(
            monkeypatch,
            [
                {"access": "ADMIN"},
                {"username": "rafastudio", "access": "ADMIN"},
            ],
        )

        res = auth_client.put("/users/1", json={"username": "outro_nome", "access": "ADMIN"})

        assert res.status_code == 403
        query.update.assert_not_called()

    def test_renaming_master_admin_case_only_change_is_blocked(self, auth_client, monkeypatch):
        """Trocar só a CAIXA (rafastudio -> Rafastudio) também é renomear."""
        query = _mock_supabase(
            monkeypatch,
            [
                {"access": "ADMIN"},
                {"username": "rafastudio", "access": "ADMIN"},
            ],
        )

        res = auth_client.put("/users/1", json={"username": "Rafastudio", "access": "ADMIN"})

        assert res.status_code == 403
        query.update.assert_not_called()

    def test_updating_other_user_still_works(self, auth_client, monkeypatch):
        query = _mock_supabase(
            monkeypatch,
            [
                {"access": "ADMIN"},
                {"username": "outro_user", "access": "USER"},
                [{"id": "2", "username": "outro_user", "access": "ADMIN"}],
            ],
        )

        res = auth_client.put("/users/2", json={"username": "outro_user", "access": "ADMIN"})

        assert res.status_code == 200
        assert res.json()["access"] == "ADMIN"
        query.update.assert_called_once()


class TestDeleteUserProtectsMasterAdmin:
    """rafastudio (master admin) nunca pode ser removido."""

    def test_deleting_master_admin_is_blocked(self, auth_client, monkeypatch):
        query = _mock_supabase(
            monkeypatch,
            [
                {"access": "ADMIN"},
                {"username": "rafastudio", "access": "ADMIN"},
            ],
        )

        res = auth_client.delete("/users/1")

        assert res.status_code == 403
        query.delete.assert_not_called()

    def test_deleting_other_user_still_works(self, auth_client, monkeypatch):
        query = _mock_supabase(
            monkeypatch,
            [
                {"access": "ADMIN"},
                {"username": "outro_user", "access": "USER"},
                [{"id": "2"}],
            ],
        )

        res = auth_client.delete("/users/2")

        assert res.status_code == 200
        query.delete.assert_called_once()

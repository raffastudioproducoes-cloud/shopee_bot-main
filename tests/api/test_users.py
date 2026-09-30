"""Testes do router de usuários (FastAPI). Admin-only — ver _require_admin."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from api import database as database_module
from api.main import app
from api.routers import auth as auth_module
from api.routers import users as users_router
from api.routers.auth import get_current_user_id

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


class TestSelfDeleteAccount:
    """DELETE /users/me — autoexclusão de conta (item 10.5 do backlog,
    LGPD/direito ao esquecimento). Qualquer usuário autenticado (não
    precisa ser admin) pode excluir a própria conta, mediante senha atual."""

    def test_requires_auth(self, client):
        res = client.request("DELETE", "/users/me", json={"current_password": "x"})
        assert res.status_code == 401

    def test_wrong_password_returns_403_and_does_not_delete(self, auth_client, monkeypatch):
        hashed = _pwd_context.hash("senha_correta")
        query = _mock_supabase(
            monkeypatch,
            [{"username": "usuario_comum", "access": "USER", "password": hashed}],
        )

        res = auth_client.request(
            "DELETE", "/users/me", json={"current_password": "senha_errada"}
        )

        assert res.status_code == 403
        query.delete.assert_not_called()

    def test_correct_password_deletes_account_clears_cookie_and_audits(
        self, auth_client, monkeypatch
    ):
        hashed = _pwd_context.hash("senha_correta")
        query = _mock_supabase(
            monkeypatch,
            [
                {"username": "usuario_comum", "access": "USER", "password": hashed},
                [{"id": "42"}],
            ],
        )
        spy = MagicMock()
        monkeypatch.setattr(users_router, "record_audit_event", spy)

        res = auth_client.request(
            "DELETE", "/users/me", json={"current_password": "senha_correta"}
        )

        assert res.status_code == 200
        query.delete.assert_called_once()
        set_cookie = res.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert 'Max-Age=0' in set_cookie or "1970" in set_cookie

        spy.assert_called_once()
        assert spy.call_args.kwargs["action"] == "user_self_deleted"
        assert spy.call_args.kwargs["entity"] == "user"
        assert spy.call_args.kwargs["user_id"] == "42"

    def test_master_admin_cannot_self_delete(self, auth_client, monkeypatch):
        hashed = _pwd_context.hash("senha_correta")
        query = _mock_supabase(
            monkeypatch,
            [{"username": "rafastudio", "access": "ADMIN", "password": hashed}],
        )

        res = auth_client.request(
            "DELETE", "/users/me", json={"current_password": "senha_correta"}
        )

        assert res.status_code == 403
        query.delete.assert_not_called()

    def test_deleted_user_can_no_longer_log_in(self, monkeypatch):
        """Depois de excluído, o usuário deixa de existir na base — login
        subsequente com as mesmas credenciais falha (usuário não encontrado)."""
        hashed = _pwd_context.hash("senha_correta")

        app.dependency_overrides.clear()
        app.dependency_overrides[get_current_user_id] = lambda: 42
        client = TestClient(app)

        _mock_supabase(
            monkeypatch,
            [
                {"username": "usuario_comum", "access": "USER", "password": hashed},
                [{"id": "42"}],
            ],
        )
        res = client.request("DELETE", "/users/me", json={"current_password": "senha_correta"})
        assert res.status_code == 200

        # Login pós-exclusão: mocka o supabase pra devolver "não encontrado"
        # (é o que a base real faria — a linha já foi apagada acima).
        app.dependency_overrides.clear()
        fake_client = MagicMock()
        fake_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        login_res = client.post(
            "/auth/login",
            data={"username": "usuario_comum", "password": "senha_correta"},
        )
        assert login_res.status_code == 401

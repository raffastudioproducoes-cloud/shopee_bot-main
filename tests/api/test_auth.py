"""Testes do router de auth (FastAPI). Foco: reset de senha self-service."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import auth as auth_module


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_reset_cooldown():
    """Evita que o cooldown de reset-password vaze entre testes."""
    auth_module._last_reset_attempt.clear()
    yield
    auth_module._last_reset_attempt.clear()


@pytest.fixture(autouse=True)
def _clear_register_cooldown():
    """Evita que o cooldown de register vaze entre testes."""
    auth_module._last_register_attempt.clear()
    yield
    auth_module._last_register_attempt.clear()


class TestResetPassword:
    def test_existing_user_updates_hashed_password(self, client, monkeypatch):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": 1, "username": "rafa", "password": "old-hash"}]
        )
        query.update.return_value = query

        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={"username": "rafa", "new_password": "nova-senha-123"},
        )

        assert res.status_code == 200
        assert res.json() == {"msg": "Se o usuário existir, a senha foi atualizada"}

        fake_client.table.assert_called_with("users")
        query.update.assert_called_once()
        (update_arg,), _ = query.update.call_args
        new_hash = update_arg["password"]
        assert new_hash != "nova-senha-123"

        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        assert pwd_context.verify("nova-senha-123", new_hash)

    def test_nonexistent_user_returns_generic_200_without_update(
        self, client, monkeypatch
    ):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(data=[])

        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={"username": "nao-existe", "new_password": "nova-senha-123"},
        )

        assert res.status_code == 200
        assert res.json() == {"msg": "Se o usuário existir, a senha foi atualizada"}
        query.update.assert_not_called()

    def test_short_password_returns_400(self, client, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={"username": "rafa", "new_password": "curta"},
        )

        assert res.status_code == 400
        fake_client.table.assert_not_called()

    def test_second_attempt_within_cooldown_returns_429_without_update(
        self, client, monkeypatch
    ):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": 1, "username": "cooldown-user", "password": "old-hash"}]
        )
        query.update.return_value = query

        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        first = client.post(
            "/auth/reset-password",
            json={"username": "cooldown-user", "new_password": "nova-senha-123"},
        )
        assert first.status_code == 200

        query.update.reset_mock()

        second = client.post(
            "/auth/reset-password",
            json={"username": "cooldown-user", "new_password": "outra-senha-456"},
        )

        assert second.status_code == 429
        query.update.assert_not_called()

    def test_password_over_72_chars_returns_400(self, client, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={"username": "long-pw-user", "new_password": "a" * 73},
        )

        assert res.status_code == 400
        fake_client.table.assert_not_called()

    def test_username_over_64_chars_rejected_by_schema(self, client, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={"username": "u" * 65, "new_password": "nova-senha-123"},
        )

        assert res.status_code == 422
        fake_client.table.assert_not_called()


class TestRegister:
    def _fake_supabase(self, existing_user=None, created=None):
        """Supabase mock com uma tabela mock por nome (evita que a checagem
        de username único e o insert em NETWORK_TABLES colidam num único
        MagicMock compartilhado)."""
        tables: dict[str, MagicMock] = {}

        def table_side_effect(name):
            if name not in tables:
                mock = MagicMock()
                mock.select.return_value = mock
                mock.eq.return_value = mock
                mock.insert.return_value = mock
                tables[name] = mock
            return tables[name]

        fake_client = MagicMock()
        fake_client.table.side_effect = table_side_effect

        users_table = table_side_effect("users")
        check_result = MagicMock(data=[existing_user] if existing_user else [])
        insert_result = MagicMock(
            data=[created or {"id": 42, "username": "newuser", "access": "USER"}]
        )
        # 1ª chamada = checagem de username único, 2ª = insert do usuário
        users_table.execute.side_effect = [check_result, insert_result]

        return fake_client, tables

    def test_new_username_returns_201(self, client, monkeypatch):
        fake_client, tables = self._fake_supabase(
            created={"id": 42, "username": "newuser", "access": "USER"}
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "12345678"},
        )

        assert res.status_code == 201
        assert res.json() == {"id": 42, "username": "newuser", "access": "USER"}
        assert "password" not in res.json()

        insert_arg = tables["users"].insert.call_args[0][0]
        assert insert_arg["access"] == "USER"

    def test_client_supplied_access_field_is_ignored(self, client, monkeypatch):
        fake_client, tables = self._fake_supabase(
            created={"id": 43, "username": "x", "access": "USER"}
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/register",
            json={"username": "x", "password": "12345678", "access": "ADMIN"},
        )

        assert res.status_code == 201
        assert res.json()["access"] == "USER"

        insert_arg = tables["users"].insert.call_args[0][0]
        assert insert_arg["access"] == "USER"

    @pytest.mark.parametrize("username", ["RafaStudio", "RAFASTUDIO", "rafastudio"])
    def test_master_admin_username_variant_returns_409_without_insert(
        self, client, monkeypatch, username
    ):
        fake_client, tables = self._fake_supabase()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/register",
            json={"username": username, "password": "12345678"},
        )

        assert res.status_code == 409
        fake_client.table.assert_not_called()

    def test_duplicate_username_returns_409(self, client, monkeypatch):
        fake_client, tables = self._fake_supabase(
            existing_user={"id": 1, "username": "dup", "password": "hash"}
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/register",
            json={"username": "dup", "password": "12345678"},
        )

        assert res.status_code == 409
        tables["users"].insert.assert_not_called()

    def test_short_password_returns_400(self, client, monkeypatch):
        fake_client, _tables = self._fake_supabase()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/register",
            json={"username": "shortpw", "password": "1234567"},
        )

        assert res.status_code == 400
        fake_client.table.assert_not_called()

    def test_second_attempt_same_ip_within_cooldown_returns_429(
        self, client, monkeypatch
    ):
        fake_client, _tables = self._fake_supabase(
            created={"id": 44, "username": "cooldown1", "access": "USER"}
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        first = client.post(
            "/auth/register",
            json={"username": "cooldown1", "password": "12345678"},
        )
        assert first.status_code == 201

        second = client.post(
            "/auth/register",
            json={"username": "cooldown2", "password": "12345678"},
        )

        assert second.status_code == 429

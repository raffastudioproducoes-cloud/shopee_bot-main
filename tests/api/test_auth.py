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

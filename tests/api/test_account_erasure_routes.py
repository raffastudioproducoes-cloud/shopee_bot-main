"""Contrato HTTP de apagamento integral após ativação explícita da flag."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import users as users_router
from api.routers.auth import get_current_user_id


@pytest.fixture
def auth_client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "00000000-0000-0000-0000-000000000042"
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_self_delete_enabled_invokes_full_eraser_and_clears_session(auth_client, monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"username": "usuario_teste", "access": "USER", "password": "hash",
              "email": None, "supabase_auth_user_id": None}
    )
    monkeypatch.setattr(users_router, "supabase", db)
    monkeypatch.setattr(users_router, "_check_login_rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(users_router, "account_erasure_enabled", lambda: True)
    check = MagicMock()
    eraser = MagicMock(return_value={"status": "deleted"})
    monkeypatch.setattr(users_router, "_verify_self_delete_password", check)
    monkeypatch.setattr(users_router, "erase_account", eraser)

    response = auth_client.request("DELETE", "/users/me", json={"current_password": "senha"})
    assert response.status_code == 200
    assert response.json()["msg"] == "Conta removida"
    eraser.assert_called_once_with("00000000-0000-0000-0000-000000000042")
    check.assert_called_once()
    db.table.return_value.delete.assert_not_called()
    assert "access_token=" in response.headers.get("set-cookie", "")


def test_admin_retry_requires_admin_role():
    app.dependency_overrides.clear()
    client = TestClient(app)
    response = client.post("/admin/users/00000000-0000-0000-0000-000000000042/erasure/retry")
    assert response.status_code == 401

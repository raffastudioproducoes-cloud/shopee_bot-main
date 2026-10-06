"""Testes do router de settings (FastAPI). Foco: troca de senha autenticada.

Diferencas em relacao ao brief original (task-8-brief.md), autorizadas no
prompt da task pra manter comportamento real testado:

1. Fixtures `client`/`auth_client` seguem o padrao real de
   tests/api/test_products.py (app.dependency_overrides sobre
   `get_current_user_id`) -- `client`/`auth_headers` com cookies reais nao
   existem em tests/api/conftest.py.
2. Mock do Supabase via `monkeypatch.setattr(database_module, "get_supabase",
   ...)` em vez de `patch("api.routers.settings.supabase")` direto -- mesmo
   motivo documentado em test_profiles.py: `supabase` e um proxy
   (`api/database.py::_SupabaseProxy`) cujo `__getattr__` chama
   `get_supabase()` de verdade, e `unittest.mock.patch` sonda
   `hasattr(obj, "__func__")` no objeto original antes de substitui-lo, o
   que dispara esse `__getattr__` e levanta `RuntimeError` (sem
   SUPABASE_URL/KEY configurados no ambiente de teste).
3. `pwd_context` nao e mockado -- e a instancia real de bcrypt (agora
   module-level em api/routers/auth.py, reusada aqui), o que exercita
   hash/verify de verdade em vez de simular o retorno.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers import auth as auth_module
from api.routers.auth import get_current_user_id, pwd_context


@pytest.fixture
def auth_client():
    """Cliente autenticado (user_id=42) -- mesmo padrao de test_products.py."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_changepw_rate_limit():
    """PUT /settings/password reusa o rate limit de login (mesmo dict de
    modulo `auth_module._login_attempts`, chave `changepw:<user_id>`) --
    evita vazar contagem de tentativa entre testes (mesmo padrao de
    test_users.py::_clear_selfdelete_rate_limit)."""
    auth_module._login_attempts.clear()
    yield
    auth_module._login_attempts.clear()


def _fake_client_for_user(user_data):
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.single.return_value = query
    query.execute.return_value = MagicMock(data=user_data)
    query.update.return_value = query
    return fake_client, query


def test_change_password_rejects_wrong_current_password(auth_client, monkeypatch):
    fake_client, query = _fake_client_for_user(
        {"id": 42, "password": pwd_context.hash("senha-antiga-1")}
    )
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    response = auth_client.put(
        "/settings/password",
        json={"current_password": "errada", "new_password": "nova12345"},
    )

    assert response.status_code == 403
    query.update.assert_not_called()


def test_change_password_updates_hash_with_correct_current_password(
    auth_client, monkeypatch
):
    fake_client, query = _fake_client_for_user(
        {"id": 42, "password": pwd_context.hash("senha-antiga-1")}
    )
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    response = auth_client.put(
        "/settings/password",
        json={"current_password": "senha-antiga-1", "new_password": "nova12345"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}
    query.update.assert_called_once()
    new_hash = query.update.call_args[0][0]["password"]
    assert pwd_context.verify("nova12345", new_hash)


def test_change_password_rejects_short_new_password(auth_client, monkeypatch):
    fake_client, query = _fake_client_for_user(
        {"id": 42, "password": pwd_context.hash("senha-antiga-1")}
    )
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    response = auth_client.put(
        "/settings/password",
        json={"current_password": "senha-antiga-1", "new_password": "123"},
    )

    assert response.status_code == 400
    query.update.assert_not_called()


def test_change_password_sixth_wrong_attempt_within_60s_returns_429(
    auth_client, monkeypatch
):
    fake_client, query = _fake_client_for_user(
        {"id": 42, "password": pwd_context.hash("senha-antiga-1")}
    )
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    responses = [
        auth_client.put(
            "/settings/password",
            json={"current_password": "errada", "new_password": "nova12345"},
        )
        for _ in range(5)
    ]
    assert all(r.status_code == 403 for r in responses)

    sixth = auth_client.put(
        "/settings/password",
        json={"current_password": "errada", "new_password": "nova12345"},
    )

    assert sixth.status_code == 429
    query.update.assert_not_called()


def test_change_password_requires_authentication():
    app.dependency_overrides.clear()
    client = TestClient(app)

    response = client.put(
        "/settings/password",
        json={"current_password": "x", "new_password": "nova12345"},
    )

    assert response.status_code == 401


def test_change_password_rejects_80_bytes_even_with_20_chars(auth_client, monkeypatch):
    """20 emojis = 20 caracteres mas 80 bytes UTF-8; bcrypt truncaria em 72."""
    fake_client, query = _fake_client_for_user(
        {"id": 42, "password": pwd_context.hash("senha-antiga-1")}
    )
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    response = auth_client.put(
        "/settings/password",
        json={"current_password": "senha-antiga-1", "new_password": "😀" * 20},
    )

    assert response.status_code == 400
    assert "72 bytes" in response.json()["detail"]
    query.update.assert_not_called()


def test_change_password_accepts_exactly_72_bytes(auth_client, monkeypatch):
    fake_client, query = _fake_client_for_user(
        {"id": 42, "password": pwd_context.hash("senha-antiga-1")}
    )
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

    response = auth_client.put(
        "/settings/password",
        json={"current_password": "senha-antiga-1", "new_password": "😀" * 18},
    )

    assert response.status_code == 200

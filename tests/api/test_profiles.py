"""Testes do router de perfis (FastAPI) -- limite de 3, perfil principal
protegido contra exclusao, e ativacao de perfil (troca de cookie).

Duas diferencas em relacao ao brief original (task-5-brief.md), ambas
autorizadas la mesmo pra manter o comportamento testado:

1. Fixtures `client`/`auth_client` seguem o padrao real de
   tests/api/test_users.py (app.dependency_overrides sobre
   `get_current_user_id`) -- `client`/`auth_headers` com cookies reais nao
   existem em tests/api/conftest.py.
2. Mock do Supabase via `monkeypatch.setattr(database_module, "get_supabase",
   ...)` -- igual test_users.py/test_auth.py -- em vez de
   `patch("api.routers.profiles.supabase")` direto: `supabase` e um proxy
   (`api/database.py::_SupabaseProxy`) cujo `__getattr__` chama
   `get_supabase()` de verdade; no Python usado aqui (3.14),
   `unittest.mock.patch` sonda `hasattr(obj, "__func__")` no objeto
   ORIGINAL antes de substitui-lo, o que disparou esse `__getattr__` e
   levantou `RuntimeError: SUPABASE_URL and SUPABASE_KEY must be
   configured` (sem SUPABASE_URL/KEY configurados no ambiente de teste).
   Patchar a funcao de origem evita o proxy ser tocado.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers.auth import _create_token, get_current_user_id

USER_ID = "u-1"


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Cliente autenticado (user_id=USER_ID) -- mesmo padrao de test_users.py."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    return TestClient(app)


def _mock_supabase(monkeypatch, execute_return):
    """Mocka `supabase.table(...)` encadeado (select/eq/maybe_single/update/
    delete/insert todos retornam o proprio mock, permitindo qualquer numero
    de `.eq(...)` em sequencia) devolvendo `execute_return` em toda chamada
    de `.execute()`."""
    fake_client = MagicMock()
    query = fake_client.table.return_value
    for method in ("select", "eq", "maybe_single", "update", "delete", "insert"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=execute_return)
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return query


def test_create_profile_blocked_when_limit_of_three_reached(auth_client, monkeypatch):
    _mock_supabase(
        monkeypatch,
        [
            {"id": "p-1", "kind": "principal"},
            {"id": "p-2", "kind": "secundario"},
            {"id": "p-3", "kind": "secundario"},
        ],
    )
    response = auth_client.post(
        "/profiles",
        json={"nome": "Loja 4", "email": "loja4@example.com"},
    )
    assert response.status_code == 400
    assert "limite" in response.json()["detail"].lower()


def test_delete_principal_profile_is_blocked(auth_client, monkeypatch):
    _mock_supabase(
        monkeypatch, {"id": "p-1", "user_id": USER_ID, "kind": "principal"}
    )
    response = auth_client.delete("/profiles/p-1")
    assert response.status_code == 400


def test_delete_secondary_profile_succeeds(auth_client, monkeypatch):
    _mock_supabase(
        monkeypatch, {"id": "p-2", "user_id": USER_ID, "kind": "secundario"}
    )
    response = auth_client.delete("/profiles/p-2")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}


def test_create_profile_requires_auth(client):
    response = client.post("/profiles", json={"nome": "Loja", "email": "a@b.com"})
    assert response.status_code == 401


def test_delete_profile_not_found_returns_404(auth_client, monkeypatch):
    _mock_supabase(monkeypatch, None)
    response = auth_client.delete("/profiles/does-not-exist")
    assert response.status_code == 404


def test_update_profile_of_another_user_returns_404(auth_client, monkeypatch):
    """IDOR: usuario A autenticado tenta PUT num profile_id que pertence ao
    usuario B -- a query `.eq('id', ...).eq('user_id', ...)` em
    `_get_own_profile_or_404` nao encontra nada (perfil e de outra conta) e
    deve devolver 404, mesmo comportamento ja testado em delete/activate."""
    _mock_supabase(monkeypatch, None)
    response = auth_client.put(
        "/profiles/p-of-another-user",
        json={"nome": "Hack", "email": "hack@example.com"},
    )
    assert response.status_code == 404


def test_activate_profile_copies_login_cookie_flags(auth_client, monkeypatch):
    """Verifica que /profiles/{id}/activate seta o cookie `access_token`
    com os MESMOS flags do login (httponly, secure, samesite=lax,
    max_age=86400) -- checagem pontual pedida no brief da Task 5."""
    token = _create_token({"sub": "testuser", "id": USER_ID})
    auth_client.cookies.set("access_token", token)

    _mock_supabase(
        monkeypatch, {"id": "p-2", "user_id": USER_ID, "kind": "secundario"}
    )
    response = auth_client.post("/profiles/p-2/activate")

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    assert "max-age=86400" in set_cookie.lower()

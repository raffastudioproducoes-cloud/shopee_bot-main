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
from api.utils.log_sanitizer import _MASK

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


@pytest.fixture(autouse=True)
def _clear_selfdelete_rate_limit():
    """DELETE /users/me agora reusa o rate limit de login (mesmo dict de
    módulo `auth_module._login_attempts`, chave `selfdelete:<user_id>`) —
    evita vazar contagem de tentativa entre testes (mesmo padrão de
    test_auth.py::_clear_login_rate_limit)."""
    auth_module._login_attempts.clear()
    yield
    auth_module._login_attempts.clear()


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


def _query_mock(execute_return) -> MagicMock:
    """Mock de query builder encadeável (mesmo padrão de test_lists.py)."""
    query = MagicMock()
    for method in (
        "select", "eq", "single", "in_", "delete", "insert", "update",
        "order", "limit", "is_", "maybe_single", "upsert",
    ):
        getattr(query, method).return_value = query
    if isinstance(execute_return, list):
        query.execute.side_effect = execute_return
    else:
        query.execute.return_value = execute_return
    return query


def _make_fake_supabase(tables: dict[str, MagicMock]) -> MagicMock:
    fake_client = MagicMock()
    fake_client.table.side_effect = lambda name: tables[name]
    return fake_client


class TestBackupExport:
    """GET /users/me/backup — item 10.8 do backlog."""

    def test_requires_auth(self, client):
        res = client.get("/users/me/backup")
        assert res.status_code == 401

    def test_export_returns_valid_checksum_and_masks_sensitive_field(self, auth_client, monkeypatch):
        # Produto com um campo "access_token" bogus — nunca deveria existir
        # de verdade na tabela `products`, mas prova que sanitize_log_data
        # mascara mesmo assim (defesa em profundidade, ver docstring do
        # endpoint e de log_sanitizer.py).
        tables = {
            "products": _query_mock(MagicMock(data=[
                {"id": 1, "user_id": 42, "name": "Produto", "price_min": "10.5",
                 "price_max": "20", "commission": "1.2", "access_token": "leak-me"},
            ])),
            "product_lists": _query_mock(MagicMock(data=[])),
            "posts": _query_mock(MagicMock(data=[])),
        }
        monkeypatch.setattr(database_module, "get_supabase", lambda: _make_fake_supabase(tables))

        res = auth_client.get("/users/me/backup")

        assert res.status_code == 200
        body = res.json()
        assert body["products"][0]["access_token"] == _MASK
        assert "checksum" in body

        # Recalcula o checksum sobre os mesmos 4 campos e confere que bate.
        data = {k: body[k] for k in ("products", "product_lists", "posts", "exported_at")}
        assert users_router._checksum(data) == body["checksum"]


class TestBackupRestore:
    """POST /users/me/restore — item 10.8 do backlog."""

    def test_requires_auth(self, client):
        res = client.post("/users/me/restore", json={
            "products": [], "product_lists": [], "posts": [],
            "exported_at": "2026-01-01T00:00:00+00:00", "checksum": "x",
        })
        assert res.status_code == 401

    def test_tampered_checksum_returns_400_and_creates_nothing(self, auth_client, monkeypatch):
        data = {
            "products": [{"id": 1, "product_id": "123", "name": "Produto"}],
            "product_lists": [],
            "posts": [],
            "exported_at": "2026-01-01T00:00:00+00:00",
        }
        checksum = users_router._checksum(data)
        tampered = ("0" if checksum[0] != "0" else "1") + checksum[1:]

        fake_client = MagicMock()
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.post("/users/me/restore", json={**data, "checksum": tampered})

        assert res.status_code == 400
        assert "corrompido" in res.json()["detail"]
        fake_client.table.assert_not_called()

    def test_valid_checksum_imports_data_as_new_records_for_current_user(self, auth_client, monkeypatch):
        data = {
            "products": [
                {"id": 1, "user_id": 999, "product_id": "123", "name": "Produto restaurado"}
            ],
            "product_lists": [],
            "posts": [],
            "exported_at": "2026-01-01T00:00:00+00:00",
        }
        checksum = users_router._checksum(data)

        tables = {
            "products": _query_mock(MagicMock(data=[{"id": 55, "name": "Produto restaurado"}])),
        }
        monkeypatch.setattr(database_module, "get_supabase", lambda: _make_fake_supabase(tables))

        res = auth_client.post("/users/me/restore", json={**data, "checksum": checksum})

        assert res.status_code == 200
        upsert_call = tables["products"].upsert.call_args
        inserted = upsert_call.args[0]
        assert inserted["user_id"] == 42  # nunca o user_id vindo do backup (999)
        assert "id" not in inserted  # allowlist do ProductCreate: sem `id` solto
        assert inserted["name"] == "Produto restaurado"
        assert upsert_call.kwargs["on_conflict"] == "product_id,user_id"

    def test_malformed_product_item_returns_422_not_500(self, auth_client, monkeypatch):
        """`product_id` ausente (fora do schema `ProductCreate`) vira 422
        claro — antes um item malformado batia direto no Supabase e podia
        derrubar a requisição com 500."""
        data = {
            "products": [{"id": 1, "name": "Sem product_id"}],
            "product_lists": [],
            "posts": [],
            "exported_at": "2026-01-01T00:00:00+00:00",
        }
        checksum = users_router._checksum(data)

        fake_client = MagicMock()
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.post("/users/me/restore", json={**data, "checksum": checksum})

        assert res.status_code == 422
        assert "product_id" in res.json()["detail"]

    def test_restoring_duplicate_product_to_same_account_upserts_instead_of_500(
        self, auth_client, monkeypatch
    ):
        """Restaurar na PRÓPRIA conta que gerou o backup é o uso normal
        (conferir/restaurar) — não pode quebrar com 500 por violar a
        constraint única (product_id, user_id) do produto que já existe."""
        data = {
            "products": [{"id": 1, "product_id": "123", "name": "Produto já existente"}],
            "product_lists": [],
            "posts": [],
            "exported_at": "2026-01-01T00:00:00+00:00",
        }
        checksum = users_router._checksum(data)

        tables = {
            "products": _query_mock(MagicMock(data=[{"id": 55, "name": "Produto já existente"}])),
        }
        monkeypatch.setattr(database_module, "get_supabase", lambda: _make_fake_supabase(tables))

        res = auth_client.post("/users/me/restore", json={**data, "checksum": checksum})

        assert res.status_code == 200
        tables["products"].upsert.assert_called_once()
        tables["products"].insert.assert_not_called()

    def test_oversized_product_list_is_rejected_before_touching_database(
        self, auth_client, monkeypatch
    ):
        """Teto de itens (item 2 da revisão): backup com produtos demais é
        rejeitado na validação do Pydantic, nunca chega a fazer 1 insert
        por item (o que travaria a event loop com listas gigantes)."""
        fake_client = MagicMock()
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        oversized = [{"product_id": str(i), "name": "x"} for i in range(
            users_router._MAX_BACKUP_PRODUCTS + 1
        )]
        res = auth_client.post("/users/me/restore", json={
            "products": oversized,
            "product_lists": [],
            "posts": [],
            "exported_at": "2026-01-01T00:00:00+00:00",
            "checksum": "irrelevante-nem-chega-a-conferir",
        })

        assert res.status_code == 422
        fake_client.table.assert_not_called()

    def test_tampered_checksum_after_hmac_switch_is_still_rejected(self, auth_client, monkeypatch):
        """Confere que o SHA-256 puro antigo (sem o segredo do servidor)
        não passa mais na validação — provaria que o checksum é
        recalculado com HMAC, não hash simples."""
        data = {
            "products": [],
            "product_lists": [],
            "posts": [],
            "exported_at": "2026-01-01T00:00:00+00:00",
        }
        import hashlib
        import json as json_module

        naive_sha256 = hashlib.sha256(
            json_module.dumps(data, sort_keys=True).encode("utf-8")
        ).hexdigest()

        fake_client = MagicMock()
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        res = auth_client.post(
            "/users/me/restore", json={**data, "checksum": naive_sha256}
        )

        assert res.status_code == 400
        fake_client.table.assert_not_called()


class TestAdminCreateUserProvisioning:
    def test_creates_principal_profile_like_register(self, auth_client, monkeypatch):
        query = _mock_supabase(
            monkeypatch,
            [{"access": "ADMIN"}]
            + [[{"id": 9, "username": "novo", "access": "USER"}]]
            + [[{"id": "x"}]] * 8,
        )
        query.insert.return_value = query

        res = auth_client.post(
            "/users", json={"username": "novo", "password": "senha1234", "access": "USER"}
        )

        assert res.status_code == 201
        inserts = [c.args[0] for c in query.insert.call_args_list]
        assert {"user_id": 9, "kind": "principal", "nome": "novo"} in inserts

    def test_failure_rolls_back_user_and_returns_generic_500(self, auth_client, monkeypatch):
        query = _mock_supabase(
            monkeypatch,
            [{"access": "ADMIN"}, [{"id": 9, "username": "novo", "access": "USER"}]],
        )
        query.insert.return_value = query
        query.execute.side_effect = [
            MagicMock(data={"access": "ADMIN"}),
            MagicMock(data=[{"id": 9, "username": "novo", "access": "USER"}]),
            Exception("segredo do banco"),
            MagicMock(data=[]),
        ]

        res = auth_client.post(
            "/users", json={"username": "novo", "password": "senha1234", "access": "USER"}
        )

        assert res.status_code == 500
        assert "segredo" not in res.text
        query.delete.assert_called_once()


class TestBackupRestoreRateLimit:
    def test_backup_is_rate_limited(self, auth_client, monkeypatch):
        monkeypatch.setattr(users_router, "_collect_backup_data", lambda uid, pid=None: {
            "products": [], "product_lists": [], "posts": [], "exported_at": "x"
        })
        codes = [auth_client.get("/users/me/backup").status_code for _ in range(6)]
        assert codes[:5] == [200] * 5
        assert codes[5] == 429

    def test_restore_is_rate_limited(self, auth_client):
        body = {"products": [], "product_lists": [], "posts": [], "exported_at": "x",
                "checksum": "invalido"}
        codes = [auth_client.post("/users/me/restore", json=body).status_code for _ in range(6)]
        assert codes[5] == 429

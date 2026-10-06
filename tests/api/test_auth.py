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


@pytest.fixture(autouse=True)
def _clear_login_rate_limit():
    """Evita que o rate limit de login vaze entre testes."""
    auth_module._login_attempts.clear()
    yield
    auth_module._login_attempts.clear()


def _hash(password: str) -> str:
    from passlib.context import CryptContext

    return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)


class TestResetPassword:
    def test_existing_user_with_correct_current_password_updates_hash(
        self, client, monkeypatch
    ):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": 1, "username": "rafa", "password": _hash("senha-antiga-1")}]
        )
        query.update.return_value = query

        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={
                "username": "rafa",
                "current_password": "senha-antiga-1",
                "new_password": "nova-senha-123",
            },
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

    def test_existing_user_with_wrong_current_password_returns_generic_200_without_update(
        self, client, monkeypatch
    ):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": 1, "username": "rafa2", "password": _hash("senha-certa-1")}]
        )
        query.update.return_value = query

        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={
                "username": "rafa2",
                "current_password": "senha-errada-1",
                "new_password": "nova-senha-123",
            },
        )

        assert res.status_code == 200
        assert res.json() == {"msg": "Se o usuário existir, a senha foi atualizada"}
        query.update.assert_not_called()

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
            json={
                "username": "nao-existe",
                "current_password": "qualquer-coisa",
                "new_password": "nova-senha-123",
            },
        )

        assert res.status_code == 200
        assert res.json() == {"msg": "Se o usuário existir, a senha foi atualizada"}
        query.update.assert_not_called()

    def test_missing_current_password_returns_422(self, client, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={"username": "rafa", "new_password": "nova-senha-123"},
        )

        assert res.status_code == 422
        fake_client.table.assert_not_called()

    def test_short_password_returns_400(self, client, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={
                "username": "rafa",
                "current_password": "senha-antiga-1",
                "new_password": "curta",
            },
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
            data=[
                {
                    "id": 1,
                    "username": "cooldown-user",
                    "password": _hash("senha-antiga-1"),
                }
            ]
        )
        query.update.return_value = query

        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        first = client.post(
            "/auth/reset-password",
            json={
                "username": "cooldown-user",
                "current_password": "senha-antiga-1",
                "new_password": "nova-senha-123",
            },
        )
        assert first.status_code == 200

        query.update.reset_mock()

        second = client.post(
            "/auth/reset-password",
            json={
                "username": "cooldown-user",
                "current_password": "nova-senha-123",
                "new_password": "outra-senha-456",
            },
        )

        assert second.status_code == 429
        query.update.assert_not_called()

    def test_password_over_72_chars_returns_400(self, client, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={
                "username": "long-pw-user",
                "current_password": "senha-antiga-1",
                "new_password": "a" * 73,
            },
        )

        assert res.status_code == 400
        fake_client.table.assert_not_called()

    def test_username_over_64_chars_rejected_by_schema(self, client, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/reset-password",
            json={
                "username": "u" * 65,
                "current_password": "senha-antiga-1",
                "new_password": "nova-senha-123",
            },
        )

        assert res.status_code == 422
        fake_client.table.assert_not_called()


class TestLoginRateLimit:
    def _fake_supabase_with_user(self, username: str, password_hash: str):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": 1, "username": username, "password": password_hash}]
        )
        return fake_client

    def test_sixth_attempt_within_60s_returns_429(self, client, monkeypatch):
        fake_client = self._fake_supabase_with_user("rate-user", _hash("senha-certa"))
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        responses = [
            client.post(
                "/auth/login",
                data={"username": "rate-user", "password": "senha-errada"},
            )
            for _ in range(5)
        ]
        assert all(r.status_code == 401 for r in responses)

        sixth = client.post(
            "/auth/login",
            data={"username": "rate-user", "password": "senha-errada"},
        )

        assert sixth.status_code == 429

    def test_rate_limit_does_not_block_different_username_from_same_ip(
        self, client, monkeypatch
    ):
        fake_client = self._fake_supabase_with_user("other-user", _hash("senha-certa"))
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        for _ in range(5):
            client.post(
                "/auth/login",
                data={"username": "exhausted-user", "password": "senha-errada"},
            )

        res = client.post(
            "/auth/login",
            data={"username": "other-user", "password": "senha-certa"},
        )

        assert res.status_code == 200


class TestStaleTokenIdRejected:
    """Item 3 da revisão de segurança: token cujo `id` não bate com o
    `id` atual do usuário daquele username não autentica. Cenário real:
    JWT emitido antes de uma autoexclusão de conta (válido até 24h)
    reusado depois que outra pessoa se cadastra com o MESMO username."""

    def _fake_supabase_with_user(self, user_id, username: str):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": user_id, "username": username, "access": "USER"}]
        )
        return fake_client

    def test_me_rejects_token_with_stale_id_for_same_username(self, client, monkeypatch):
        # Token emitido pra id=1 ("usuario"), mas a base hoje tem um id=2
        # com o mesmo username (a conta original foi apagada e o nome
        # foi reaproveitado por um cadastro novo).
        stale_token = auth_module._create_token({"sub": "usuario", "id": 1})
        fake_client = self._fake_supabase_with_user(2, "usuario")
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        client.cookies.set("access_token", stale_token)
        res = client.get("/auth/me")

        assert res.status_code == 401

    def test_me_accepts_token_with_matching_id(self, client, monkeypatch):
        token = auth_module._create_token({"sub": "usuario", "id": 2})
        fake_client = self._fake_supabase_with_user(2, "usuario")
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        client.cookies.set("access_token", token)
        res = client.get("/auth/me")

        assert res.status_code == 200
        assert res.json()["id"] == 2

    def test_get_current_user_id_rejects_stale_id(self, monkeypatch):
        """Mesma checagem, direto na dependência usada por todo endpoint
        autenticado (não só `/auth/me`)."""
        from types import SimpleNamespace

        from fastapi import HTTPException

        stale_token = auth_module._create_token({"sub": "usuario", "id": 1})
        fake_client = self._fake_supabase_with_user(2, "usuario")
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        fake_request = SimpleNamespace(cookies={"access_token": stale_token})
        with pytest.raises(HTTPException) as exc_info:
            auth_module.get_current_user_id(fake_request)
        assert exc_info.value.status_code == 401


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

    def test_new_user_gets_principal_profile_created(self, client, monkeypatch):
        """Sem isso, contas criadas via /auth/register nunca ganham perfil
        "principal" (a migração 035 só fez backfill dos usuários já
        existentes) -- o primeiro perfil que o usuário criasse via
        POST /profiles nasceria "secundario" (hardcoded lá)."""
        fake_client, tables = self._fake_supabase(
            created={"id": 42, "username": "newuser", "access": "USER"}
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "12345678"},
        )

        assert res.status_code == 201
        tables["profiles"].insert.assert_called_once_with({
            "user_id": 42,
            "kind": "principal",
            "nome": "newuser",
        })

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


class TestPasswordVersionClaim:
    """Token emitido antes da troca de senha (claim `pwv` com o fingerprint
    do hash antigo) deixa de autenticar; token sem o claim (legado) segue
    valendo até expirar."""

    def _fake_supabase(self, monkeypatch, password_hash):
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": 1, "username": "u", "access": "USER", "password": password_hash}]
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

    def test_token_with_old_password_version_is_rejected(self, client, monkeypatch):
        old = auth_module._create_token(
            {"sub": "u", "id": 1, "pwv": auth_module._password_version("hash-antigo")}
        )
        self._fake_supabase(monkeypatch, "hash-novo")
        client.cookies.set("access_token", old)
        assert client.get("/auth/me").status_code == 401

    def test_token_with_current_password_version_is_accepted(self, client, monkeypatch):
        token = auth_module._create_token(
            {"sub": "u", "id": 1, "pwv": auth_module._password_version("hash-atual")}
        )
        self._fake_supabase(monkeypatch, "hash-atual")
        client.cookies.set("access_token", token)
        assert client.get("/auth/me").status_code == 200

    def test_legacy_token_without_claim_still_accepted(self, client, monkeypatch):
        token = auth_module._create_token({"sub": "u", "id": 1})
        self._fake_supabase(monkeypatch, "qualquer")
        client.cookies.set("access_token", token)
        assert client.get("/auth/me").status_code == 200

    def test_login_token_carries_password_version(self, client, monkeypatch):
        h = auth_module.pwd_context.hash("senha12345")
        self._fake_supabase(monkeypatch, h)
        res = client.post("/auth/login", data={"username": "u", "password": "senha12345"})
        assert res.status_code == 200
        payload = auth_module._decode_token(res.cookies["access_token"])
        assert payload["pwv"] == auth_module._password_version(h)


class TestRegisterProvisioningFailure:
    def test_failed_profile_insert_rolls_back_user_and_returns_generic_500(
        self, client, monkeypatch
    ):
        tables: dict[str, MagicMock] = {}

        def table_side_effect(name):
            if name not in tables:
                mock = MagicMock()
                for method in ("select", "eq", "insert", "delete"):
                    getattr(mock, method).return_value = mock
                tables[name] = mock
            return tables[name]

        fake_client = MagicMock()
        fake_client.table.side_effect = table_side_effect
        table_side_effect("users").execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[{"id": 7, "username": "novo", "access": "USER"}]),
            MagicMock(data=[]),  # delete de rollback
        ]
        table_side_effect("profiles").execute.side_effect = Exception("db detalhe interno")
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)

        res = client.post("/auth/register", json={"username": "novo", "password": "12345678"})

        assert res.status_code == 500
        assert "interno" not in res.text
        tables["users"].delete.assert_called_once()
        tables["users"].eq.assert_called_with("id", 7)


class TestMeProfileId:
    """`/auth/me` expõe o perfil ativo (claim do cookie httpOnly) já validado."""

    @staticmethod
    def _setup(client, monkeypatch, claims, resolved):
        from api.routers import profiles as profiles_module

        token = auth_module._create_token({"sub": "usuario", "id": 2, **claims})
        fake_client = MagicMock()
        query = fake_client.table.return_value
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[{"id": 2, "username": "usuario", "access": "USER"}]
        )
        monkeypatch.setattr(auth_module, "get_supabase", lambda: fake_client)
        calls = []
        monkeypatch.setattr(
            profiles_module,
            "_resolve_profile_id",
            lambda pid, uid: calls.append((pid, uid)) or resolved,
        )
        client.cookies.set("access_token", token)
        return calls

    def test_me_returns_validated_profile_id(self, client, monkeypatch):
        calls = self._setup(client, monkeypatch, {"profile_id": "p-alheio"}, "p-main")
        body = client.get("/auth/me").json()
        assert body["profile_id"] == "p-main"
        assert calls == [("p-alheio", 2)]
        assert body["id"] == 2 and body["username"] == "usuario"

    def test_me_profile_id_falls_back_to_principal_without_claim(self, client, monkeypatch):
        # Coerente com get_current_profile_id: token legado sem claim opera
        # (e é reportado) no perfil principal, não "sem perfil".
        calls = self._setup(client, monkeypatch, {}, "p-main")
        assert client.get("/auth/me").json()["profile_id"] == "p-main"
        assert calls == [(None, 2)]

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


class TestSaveCredentialStripsWhitespace:
    """Copiar/colar do painel da rede (Meta for Developers, TikTok for
    Developers, etc.) facilmente traz espaço em branco líder/de trás —
    isso quebra client_key=/client_id= na URL de autorização OAuth sem
    nenhum erro visível (bug encontrado em produção no TikTok, ver
    api/routers/credentials.py::save_credential)."""

    def test_save_credential_strips_app_id_and_secret(self, monkeypatch, auth_client):
        captured = {}

        def fake_upsert(table, user_id, data, profile_id=None):
            captured["data"] = data
            return {**data, "id": 1}

        from api.routers import credentials as credentials_module

        monkeypatch.setattr(credentials_module, "_upsert_by_user", fake_upsert)
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}])

        res = auth_client.put(
            "/credentials/kwai",
            json={"app_id": " app-with-space ", "secret": " secret-with-space "},
        )

        assert res.status_code == 200
        assert captured["data"]["app_id"] == "app-with-space"
        # secret é cifrado antes de salvar — comparamos com o valor
        # descriptografado pra confirmar que o espaço não sobreviveu.
        assert credentials_module.decrypt(captured["data"]["secret"]) == "secret-with-space"


class TestTestConnectionAdminGate:
    """"Testar conexão" (POST /credentials/{network}/test): qualquer usuário
    testa a PRÓPRIA credencial (escopo user_id/perfil); o que continua
    admin-only são os overrides manuais (PUT /{network}/manual)."""

    def test_requires_auth(self, client):
        res = client.post("/credentials/shopee/test")
        assert res.status_code == 401

    def test_regular_user_can_test_own_credential(self, monkeypatch, auth_client):
        from api.routers import credentials as credentials_module

        credentials_module._test_attempts.clear()
        # sem credencial salva -> 400 (não 403): usuário comum chega no teste
        query = _mock_supabase(monkeypatch, [None])
        res = auth_client.post("/credentials/shopee/test")
        assert res.status_code == 400
        query.eq.assert_any_call("user_id", 42)

    def test_admin_without_saved_credential_returns_400(self, monkeypatch, auth_client):
        # 1ª execute: _require_admin (access=ADMIN); 2ª: busca da credencial
        # (nenhuma linha salva) — sem credencial, nada a testar.
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None])
        res = auth_client.post("/credentials/shopee/test")
        assert res.status_code == 400

    def test_admin_test_x_without_global_app_configured_returns_400(self, monkeypatch, auth_client):
        """X_CLIENT_ID/SECRET não setados no ambiente (caso comum em dev/CI)
        — nada a testar, mesmo que o usuário já tenha token OAuth salvo."""
        from api.routers import credentials as credentials_module

        monkeypatch.setattr(credentials_module.x_oauth, "CLIENT_ID", None)
        monkeypatch.setattr(credentials_module.x_oauth, "CLIENT_SECRET", None)
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}])
        res = auth_client.post("/credentials/x/test")
        assert res.status_code == 400


class TestSimpleNetworksNoLongerAcceptXTiktokInstagram:
    """x/tiktok/instagram/facebook saíram de SIMPLE_NETWORKS na migração
    pro app único (2026-09-28) — o formulário manual de App ID/Secret não
    existe mais pra essas redes, só o botão "Conectar" (authorize/callback)."""

    @pytest.mark.parametrize("network", ["x", "tiktok", "instagram", "facebook"])
    def test_put_rejects_manual_app_id_secret(self, auth_client, network):
        res = auth_client.put(
            f"/credentials/{network}",
            json={"app_id": "a", "secret": "s"},
        )
        assert res.status_code == 404


class TestManualOverrideAdminGate:
    """Entradas manuais de redes sociais (incluindo Threads/Kwai) —
    override manual admin-only, mesma dependência de POST /{network}/test.
    Requer auth + ADMIN antes de qualquer coisa; usuário comum recebe 403."""

    _BODIES = {
        "threads": {"t_user_id": "123", "access_token": "tok"},
        "x/manual": {"user_access_token": "tok"},
        "facebook/manual": {"page_id": "123", "page_access_token": "tok"},
        "tiktok/manual": {"open_id": "abc", "user_access_token": "tok"},
        "instagram/manual": {"ig_user_id": "abc", "user_access_token": "tok"},
        "kwai": {"app_id": "app", "secret": "secret"},
    }

    @pytest.mark.parametrize("path", list(_BODIES.keys()))
    def test_requires_auth(self, client, path):
        res = client.put(f"/credentials/{path}", json=self._BODIES[path])
        assert res.status_code == 401

    @pytest.mark.parametrize("path", list(_BODIES.keys()))
    def test_requires_admin(self, monkeypatch, auth_client, path):
        _mock_supabase(monkeypatch, [{"access": "USER"}])
        res = auth_client.put(f"/credentials/{path}", json=self._BODIES[path])
        assert res.status_code == 403

    def test_admin_can_save_x_manual(self, monkeypatch, auth_client):
        # 1ª execute: _require_admin; 2ª: _upsert_by_user (select existing,
        # nenhuma linha -> insert); 3ª: insert.
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None, [{"id": 1}], None])
        res = auth_client.put(
            "/credentials/x/manual",
            json={"user_access_token": "tok", "user_refresh_token": "refresh"},
        )
        assert res.status_code == 200
        assert res.json() == {"connected": True}

    def test_admin_can_save_threads_manual(self, monkeypatch, auth_client):
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None, [{"id": 1}], None])
        res = auth_client.put(
            "/credentials/threads",
            json={"t_user_id": "123", "access_token": "tok"},
        )
        assert res.status_code == 200
        assert res.json() == {"connected": True}

    def test_admin_can_save_facebook_manual(self, monkeypatch, auth_client):
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None, [{"id": 1}], None])
        res = auth_client.put(
            "/credentials/facebook/manual",
            json={"page_id": "123", "page_access_token": "tok", "page_name": "Minha Página"},
        )
        assert res.status_code == 200
        assert res.json() == {"connected": True}

    def test_admin_can_save_tiktok_manual(self, monkeypatch, auth_client):
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None, [{"id": 1}], None])
        res = auth_client.put(
            "/credentials/tiktok/manual",
            json={"open_id": "abc", "user_access_token": "tok", "refresh_token": "refresh"},
        )
        assert res.status_code == 200
        assert res.json() == {"connected": True}

    def test_admin_can_save_instagram_manual(self, monkeypatch, auth_client):
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None, [{"id": 1}], None])
        res = auth_client.put(
            "/credentials/instagram/manual",
            json={"ig_user_id": "abc", "user_access_token": "tok"},
        )
        assert res.status_code == 200
        assert res.json() == {"connected": True}

    def test_admin_can_save_kwai_manual(self, monkeypatch, auth_client):
        _mock_supabase(monkeypatch, [{"access": "ADMIN"}, None, [{"id": 1}], None])
        res = auth_client.put(
            "/credentials/kwai",
            json={"app_id": "app", "secret": "secret"},
        )
        assert res.status_code == 200
        assert res.json() == {"connected": True}


class TestDedicatedOAuthDeleteEndpoints:
    """x/tiktok/instagram têm DELETE dedicado (zeram token OAuth) desde
    que saíram do handler genérico de SIMPLE_NETWORKS."""

    def test_delete_x_zeroes_oauth_token_fields(self, monkeypatch, auth_client):
        query = _mock_supabase(monkeypatch, [{"id": 1, "status": False}])
        res = auth_client.delete("/credentials/x")
        assert res.status_code == 200
        assert res.json() == {"connected": False}
        update_data = query.update.call_args[0][0]
        assert update_data["user_access_token"] is None
        assert update_data["status"] is False

    def test_delete_tiktok_zeroes_oauth_token_fields(self, monkeypatch, auth_client):
        query = _mock_supabase(monkeypatch, [{"id": 1, "status": False}])
        res = auth_client.delete("/credentials/tiktok")
        assert res.status_code == 200
        update_data = query.update.call_args[0][0]
        assert update_data["user_access_token"] is None
        assert update_data["refresh_token"] is None
        assert update_data["open_id"] is None

    def test_delete_instagram_zeroes_oauth_token_fields(self, monkeypatch, auth_client):
        query = _mock_supabase(monkeypatch, [{"id": 1, "status": False}])
        res = auth_client.delete("/credentials/instagram")
        assert res.status_code == 200
        update_data = query.update.call_args[0][0]
        assert update_data["user_access_token"] is None
        assert update_data["ig_user_id"] is None

    def test_delete_facebook_zeroes_oauth_token_fields(self, monkeypatch, auth_client):
        query = _mock_supabase(monkeypatch, [{"id": 1, "status": False}])
        res = auth_client.delete("/credentials/facebook")
        assert res.status_code == 200
        update_data = query.update.call_args[0][0]
        assert update_data["page_access_token"] is None
        assert update_data["page_id"] is None
        assert update_data["page_name"] is None


class TestRoleSeparation:
    """Matriz papel x funcionalidade checada no BACKEND (não só no front):
    rotas administrativas devolvem 403 pro usuário comum antes de qualquer
    efeito; as da própria conexão (conectar/desconectar/testar) são de
    qualquer usuário, sempre escopadas no user_id da sessão."""

    _ADMIN_ONLY = [
        ("get", "/logs", None),
        ("get", "/users", None),
        ("post", "/users", {"username": "u", "password": "p" * 12, "access": "USER"}),
        ("get", "/users/7", None),
        ("put", "/users/7", {"access": "ADMIN"}),
        ("delete", "/users/7", None),
        ("put", "/credentials/threads", {"t_user_id": "1", "access_token": "t"}),
        ("put", "/credentials/tiktok/manual", {"open_id": "a", "user_access_token": "t"}),
        ("put", "/credentials/x/manual", {"user_access_token": "t"}),
        ("put", "/credentials/facebook/manual", {"page_id": "1", "page_access_token": "t"}),
        ("put", "/credentials/instagram/manual", {"ig_user_id": "a", "user_access_token": "t"}),
        ("put", "/credentials/kwai", {"app_id": "a", "secret": "t"}),
        ("delete", "/credentials/kwai", None),
    ]

    @pytest.mark.parametrize("method,path,body", _ADMIN_ONLY)
    def test_regular_user_gets_403_on_admin_only(self, monkeypatch, auth_client, method, path, body):
        query = _mock_supabase(monkeypatch, [{"access": "USER"}])
        kwargs = {"json": body} if body is not None else {}
        res = getattr(auth_client, method)(path, **kwargs)
        assert res.status_code == 403
        query.insert.assert_not_called()
        query.update.assert_not_called()
        query.delete.assert_not_called()

    def test_regular_user_disconnects_only_own_tiktok(self, monkeypatch, auth_client):
        query = _mock_supabase(monkeypatch, [[{"id": 1}]])
        res = auth_client.delete("/credentials/tiktok")
        assert res.status_code == 200
        query.eq.assert_any_call("user_id", 42)

    @pytest.mark.parametrize("access,sees_detail", [("USER", False), ("ADMIN", True)])
    def test_check_message_detail_is_admin_only(self, monkeypatch, auth_client, access, sees_detail):
        check = {"network": "tiktok", "state": "error", "message": "detalhe interno", "checked_at": None}
        # users(access), credential_checks, depois 1 select por rede (2 simples + 5 OAuth)
        _mock_supabase(monkeypatch, [{"access": access}, [check]] + [None] * 7)
        res = auth_client.get("/credentials")
        assert res.status_code == 200
        tiktok = res.json()["tiktok"]
        assert (tiktok["check_message"] == "detalhe interno") is sees_detail
        assert tiktok["light"] == "red"  # sem token salvo

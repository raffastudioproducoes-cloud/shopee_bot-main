"""Contrato de autenticação Supabase/Auth sem chamadas externas ou gravações reais."""
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient

from api.main import app
from api.routers import supabase_auth as sb
from api.routers import auth as legacy_auth
from api.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "supabase_auth_enabled", False)
    monkeypatch.setattr(settings, "supabase_auth_email_signup_enabled", False)
    monkeypatch.setattr(settings, "supabase_auth_publishable_key", "")
    monkeypatch.setattr(settings, "supabase_auth_redirect_base_url", "")
    monkeypatch.setattr(settings, "supabase_legacy_support_username", "")
    return TestClient(app, base_url="https://testserver")


def _enable(monkeypatch):
    monkeypatch.setattr(settings, "supabase_auth_enabled", True)
    monkeypatch.setattr(settings, "supabase_auth_email_signup_enabled", True)
    monkeypatch.setattr(settings, "supabase_auth_publishable_key", "sb_publishable_example")
    monkeypatch.setattr(settings, "supabase_auth_redirect_base_url", "https://app.example.com")
    monkeypatch.setattr(settings, "supabase_url", "https://auth.example.com")


def test_capabilities_are_disabled_by_default(client):
    response = client.get("/auth/supabase/config")
    assert response.status_code == 200
    assert response.json() == {"email_enabled": False, "email_signup_enabled": False, "google_enabled": False, "legacy_support_enabled": False}


def test_registration_never_falls_back_to_legacy(client):
    response = client.post("/auth/supabase/register", json={
        "username": "clienteteste", "email": "cliente@example.com",
        "full_name": "Cliente Teste", "cpf": "52998224725",
        "password": "minhasenhasegura", "confirm_password": "minhasenhasegura",
        "accepted_terms_version": "2026-10-31",
    })
    assert response.status_code == 503


def test_registration_rejects_password_mismatch_before_auth_call(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    monkeypatch.setattr(sb, "_auth_client", lambda: pytest.fail("não deve consultar GoTrue"))
    response = client.post("/auth/supabase/register", json={
        "username": "clienteteste", "email": "cliente@example.com",
        "full_name": "Cliente Teste", "cpf": "52998224725",
        "password": "minhasenhasegura", "confirm_password": "senhadiferente",
        "accepted_terms_version": "2026-10-31",
    })
    assert response.status_code == 422


@pytest.mark.parametrize("email", ["rafacelle27", "a@b", "a@b.c", "a@b.12", "a b@exemplo.com", "a@@exemplo.com"])
def test_registration_rejects_malformed_email_before_auth_call(client, monkeypatch, email):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    monkeypatch.setattr(sb, "ensure_password_not_breached", lambda password: _noop())
    monkeypatch.setattr(sb, "_auth_client", lambda: pytest.fail("não deve consultar GoTrue"))
    response = client.post("/auth/supabase/register", json={
        "username": "clienteteste", "email": email,
        "full_name": "Cliente Teste", "cpf": "52998224725",
        "password": "minhasenhasegura", "confirm_password": "minhasenhasegura",
        "accepted_terms_version": "2026-10-31",
    })
    assert response.status_code == 422


@pytest.mark.parametrize("cpf", ["00000000000", "11111111111", "52998224726", "123", "abcdefghijk"])
def test_registration_rejects_invalid_cpf_before_auth_call(client, monkeypatch, cpf):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    monkeypatch.setattr(sb, "_auth_client", lambda: pytest.fail("não deve consultar GoTrue"))
    response = client.post("/auth/supabase/register", json={
        "username": "clienteteste", "email": "cliente@example.com",
        "full_name": "Cliente Teste", "cpf": cpf,
        "password": "minhasenhasegura", "confirm_password": "minhasenhasegura",
        "accepted_terms_version": "2026-10-31",
    })
    assert response.status_code == 422


async def _noop():
    return None


def test_google_identity_verified_via_supabase_user_endpoint(client, monkeypatch):
    """OAuth usa o JWT entregue pelo GoTrue, sem exigir SDK com sb_publishable."""
    _enable(monkeypatch)
    called = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "auth-google-123", "email": "alguem@gmail.com"}

    class FakeHttp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers):
            called.update(url=url, headers=headers)
            return FakeResponse()

    monkeypatch.setattr(sb.httpx, "Client", lambda timeout: FakeHttp())
    monkeypatch.setattr(sb, "_auth_client", lambda: pytest.fail("não criar sessão SDK"))
    identity = sb._verify_google_token("token-temporario")
    assert identity.id == "auth-google-123"
    assert identity.email == "alguem@gmail.com"
    assert called["url"] == "https://auth.example.com/auth/v1/user"
    assert called["headers"]["apikey"] == "sb_publishable_example"
    assert called["headers"]["Authorization"] == "Bearer token-temporario"


def test_google_identity_missing_email_fails_closed(client, monkeypatch):
    _enable(monkeypatch)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "auth-google-123"}

    class FakeHttp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers):
            return FakeResponse()

    monkeypatch.setattr(sb.httpx, "Client", lambda timeout: FakeHttp())
    with pytest.raises(sb.HTTPException) as error:
        sb._verify_google_token("token-temporario")
    assert error.value.status_code == 401


def test_google_pkce_uses_secure_timed_cookie(client, monkeypatch):
    _enable(monkeypatch)
    response = client.get("/auth/supabase/google/authorize", follow_redirects=False)
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["provider"] == ["google"]
    assert query["redirect_to"] == ["https://app.example.com/api/auth/supabase/google/callback"]
    assert query["code_challenge_method"] == ["s256"]
    token = jwt.decode(response.cookies["sb_google_pkce"], settings.api_secret_key, algorithms=["HS256"])
    assert token["purpose"] == "supabase-google-pkce"
    expected = base64.urlsafe_b64encode(hashlib.sha256(token["verifier"].encode()).digest()).decode().rstrip("=")
    assert query["code_challenge"] == [expected]
    assert "secure" in response.headers["set-cookie"].lower()
    assert "httponly" in response.headers["set-cookie"].lower()


def test_google_callback_without_pkce_cookie_fails_closed(client, monkeypatch):
    _enable(monkeypatch)
    response = client.get("/auth/supabase/google/callback?code=forged", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?google_error=1"


def test_google_completion_requires_pending_auth(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    response = client.post("/auth/supabase/google/complete", json={
        "username": "novousuario", "full_name": "Cliente Teste", "cpf": "52998224725",
        "accepted_terms_version": "2026-10-31",
    })
    assert response.status_code == 401


def test_email_signup_is_pending_until_validation(client, monkeypatch, fake_db):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    db = fake_db({"users": [], "pending_auth_registrations": []})
    monkeypatch.setattr(sb, "get_supabase", lambda: db)

    captured = {}
    class FakeAuth:
        def sign_up(self, values):
            captured.update(values)
            return SimpleNamespace(user=SimpleNamespace(id="external-1"), session=None)
    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    result = client.post("/auth/supabase/register", json={
        "username": "novocliente", "email": "cliente@example.com",
        "full_name": "Cliente Teste", "cpf": "52998224725",
        "password": "senhasegura123", "confirm_password": "senhasegura123",
        "accepted_terms_version": "2026-10-31",
    })
    assert result.status_code == 202
    assert result.json()["email_confirmation_required"] is True
    assert captured["options"]["email_redirect_to"] == "https://app.example.com/login"
    assert db.tables["users"] == []
    assert len(db.tables["pending_auth_registrations"]) == 1
    pending = db.tables["pending_auth_registrations"][0]
    assert pending["full_name"] == "Cliente Teste"
    assert pending["cpf_ciphertext"] != "52998224725"
    assert "52998224725" not in str(pending)
    assert len(pending["cpf_fingerprint"]) == 64


def test_login_email_not_confirmed_cannot_enter(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    class FakeAuth:
        def sign_in_with_password(self, values):
            return SimpleNamespace(
                user=SimpleNamespace(id="external-1", email_confirmed_at=None),
                session=object(),
            )
    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    result = client.post("/auth/supabase/login", json={
        "email": "cliente@example.com", "password": "senhasegura123",
    })
    assert result.status_code == 403
    assert "Confirme seu e-mail" in result.json()["detail"]


def test_legacy_password_login_is_disabled_when_supabase_enabled(client, monkeypatch):
    _enable(monkeypatch)
    result = client.post("/auth/login", data={
        "username": "legado", "password": "senha12345",
    })
    assert result.status_code == 410


def test_legacy_support_only_when_explicitly_enabled(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(settings, "supabase_legacy_support_username", "RafaelTesteCliente")
    caps = client.get("/auth/supabase/config")
    assert caps.status_code == 200
    assert caps.json()["legacy_support_enabled"] is True

    # Outras contas continuam bloqueadas, mesmo com login legado válido.
    blocked = client.post("/auth/login", data={
        "username": "rafastudio", "password": "senhaantigavalida",
    })
    assert blocked.status_code == 410


def test_legacy_support_account_can_still_login(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(settings, "supabase_legacy_support_username", "RafaelTesteCliente")
    monkeypatch.setattr(legacy_auth, "_check_login_rate_limit", lambda key: None)
    password = "senha-testes-exclusiva"
    local_user = {
        "id": "support-user-uuid", "username": "RafaelTesteCliente",
        "access": "USER", "password": legacy_auth.pwd_context.hash(password),
        "supabase_auth_user_id": None,
    }
    monkeypatch.setattr(legacy_auth, "_get_user_from_supabase", lambda name: local_user)

    class FakeProfileQuery:
        def table(self, name):
            return self

        def select(self, fields):
            return self

        def eq(self, field, value):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            return SimpleNamespace(data={"id": "support-profile-uuid"})

    monkeypatch.setattr(legacy_auth, "get_supabase", lambda: FakeProfileQuery())
    result = client.post("/auth/login", data={
        "username": "RafaelTesteCliente", "password": password,
    })
    assert result.status_code == 200
    assert "access_token=" in result.headers.get("set-cookie", "")

    wrong = client.post("/auth/login", data={
        "username": "RafaelTesteCliente", "password": "senha-incorreta",
    })
    assert wrong.status_code == 401


def test_signup_fails_closed_if_confirm_email_is_disabled(client, monkeypatch, fake_db):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    db = fake_db({"users": [], "pending_auth_registrations": []})
    monkeypatch.setattr(sb, "get_supabase", lambda: db)
    class FakeAuth:
        def sign_up(self, values):
            return SimpleNamespace(user=SimpleNamespace(id="external-1"), session=object())
    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    result = client.post("/auth/supabase/register", json={
        "username": "novocliente", "email": "cliente@example.com",
        "full_name": "Cliente Teste", "cpf": "52998224725",
        "password": "senhasegura123", "confirm_password": "senhasegura123",
        "accepted_terms_version": "2026-10-31",
    })
    assert result.status_code == 503
    assert db.tables["users"] == []
    assert db.tables["pending_auth_registrations"] == []



def test_first_confirmed_login_provisions_only_after_email_verification(client, monkeypatch, fake_db):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key: None)
    db = fake_db({
        "users": [],
        "profiles": [],
        "pending_auth_registrations": [{
            "auth_user_id": "external-1", "email": "cliente@example.com",
            "username": "novocliente", "legal_terms_version": sb.TERMS_VERSION,
        }],
    })
    monkeypatch.setattr(sb, "get_supabase", lambda: db)
    monkeypatch.setattr(sb, "provision_new_user", lambda database, user: database.table("profiles").insert({
        "user_id": user["id"], "kind": "principal",
    }).execute())

    class FakeAuth:
        def sign_in_with_password(self, values):
            return SimpleNamespace(
                user=SimpleNamespace(
                    id="external-1", email="cliente@example.com",
                    email_confirmed_at="2026-11-01T02:00:00Z",
                ),
                session=object(),
            )

    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    values = {"email": "cliente@example.com", "password": "senhasegura123"}
    assert db.tables["users"] == []
    first = client.post("/auth/supabase/login", json=values)
    assert first.status_code == 200
    assert "access_token" in first.cookies
    assert len(db.tables["users"]) == 1
    assert db.tables["users"][0]["access"] == "USER"
    assert db.tables["users"][0]["password"] is None
    assert db.tables["users"][0]["supabase_auth_user_id"] == "external-1"
    assert db.tables["pending_auth_registrations"] == []

    second = client.post("/auth/supabase/login", json=values)
    assert second.status_code == 200
    assert len(db.tables["users"]) == 1


def test_password_recovery_request_uses_supabase_mailer_not_legacy(client, monkeypatch):
    _enable(monkeypatch)
    keys = []
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key, detail=None: keys.append(key))
    observed = {}

    class FakeAuth:
        def reset_password_for_email(self, email, options):
            observed.update(email=email, options=options)

    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    result = client.post("/auth/supabase/password/recovery", json={"email": " Person@Example.com "})
    assert result.status_code == 202
    assert "Se existir uma conta" in result.json()["msg"]
    assert observed == {
        "email": "person@example.com",
        "options": {"redirect_to": "https://app.example.com/login"},
    }
    assert any(k.startswith("supabase-recovery-email:") for k in keys)
    assert any(k.startswith("supabase-recovery-ip:") for k in keys)


def test_password_recovery_is_disabled_until_supabase_is_enabled(client):
    result = client.post("/auth/supabase/password/recovery", json={"email": "cliente@example.com"})
    assert result.status_code == 503


def test_password_recovery_does_not_expose_provider_email_failures(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key, detail=None: None)

    class FakeAuth:
        def reset_password_for_email(self, email, options):
            raise RuntimeError("private_provider_detail")

    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    result = client.post("/auth/supabase/password/recovery", json={"email": "cliente@example.com"})
    assert result.status_code == 503
    assert "private_provider_detail" not in result.text


def test_password_recovery_rejects_mismatched_passwords_before_token_verification(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key, detail=None: None)
    monkeypatch.setattr(sb, "_auth_client", lambda: pytest.fail("não deve validar token"))
    result = client.post("/auth/supabase/password/complete", json={
        "access_token": "token-simulado-valido-longo",
        "new_password": "senhasegura123",
        "confirm_password": "senhadiferente",
    })
    assert result.status_code == 422


def test_password_recovery_rejects_invalid_link_without_updating_password(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key, detail=None: None)

    class FakeAuth:
        def get_user(self, token):
            raise RuntimeError("invalid_grant")

    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    result = client.post("/auth/supabase/password/complete", json={
        "access_token": "token-simulado-invalido-longo",
        "new_password": "senhasegura123",
        "confirm_password": "senhasegura123",
    })
    assert result.status_code == 401
    assert "Link de recuperação" in result.json()["detail"]


def test_password_recovery_rejects_unconfirmed_identity(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key, detail=None: None)

    class FakeAuth:
        def get_user(self, token):
            return SimpleNamespace(user=SimpleNamespace(id="ext-1", email_confirmed_at=None))

    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))
    result = client.post("/auth/supabase/password/complete", json={
        "access_token": "token-simulado-unconfirmed",
        "new_password": "senhasegura123",
        "confirm_password": "senhasegura123",
    })
    assert result.status_code == 401


def test_password_recovery_updates_only_supabase_auth_with_verified_bearer(client, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sb, "_check_login_rate_limit", lambda key, detail=None: None)
    captured = {}

    class FakeAuth:
        def get_user(self, token):
            captured["verified_token"] = token
            return SimpleNamespace(user=SimpleNamespace(id="ext-1", email_confirmed_at="2026-11-01T00:00:00Z"))

    monkeypatch.setattr(sb, "_auth_client", lambda: SimpleNamespace(auth=FakeAuth()))

    class FakeHttp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def put(self, url, headers, json):
            captured.update(url=url, headers=headers, body=json)
            return sb.httpx.Response(200, json={"id": "ext-1"}, request=sb.httpx.Request("PUT", url))

    monkeypatch.setattr(sb.httpx, "Client", lambda timeout: FakeHttp())
    token = "token-verificado-do-link"
    result = client.post("/auth/supabase/password/complete", json={
        "access_token": token,
        "new_password": "senhasegura123",
        "confirm_password": "senhasegura123",
    })
    assert result.status_code == 200
    assert "Senha redefinida" in result.json()["msg"]
    assert captured["verified_token"] == token
    assert captured["url"] == "https://auth.example.com/auth/v1/user"
    assert captured["headers"]["Authorization"] == f"Bearer {token}"
    assert captured["headers"]["apikey"] == "sb_publishable_example"
    assert captured["body"] == {"password": "senhasegura123"}


def test_settings_password_route_cannot_write_local_password_after_cutover(client, monkeypatch):
    from api.routers import settings as settings_router

    _enable(monkeypatch)
    app.dependency_overrides[settings_router.get_current_user_id] = lambda: "user-existing"
    try:
        result = client.put("/settings/password", json={
            "current_password": "senhaantiga",
            "new_password": "senhanova123",
        })
        assert result.status_code == 410
    finally:
        app.dependency_overrides.pop(settings_router.get_current_user_id, None)

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
from api.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "supabase_auth_enabled", False)
    monkeypatch.setattr(settings, "supabase_auth_email_signup_enabled", False)
    monkeypatch.setattr(settings, "supabase_auth_publishable_key", "")
    monkeypatch.setattr(settings, "supabase_auth_redirect_base_url", "")
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
    assert response.json() == {"email_enabled": False, "email_signup_enabled": False, "google_enabled": False}


def test_registration_never_falls_back_to_legacy(client):
    response = client.post("/auth/supabase/register", json={
        "username": "clienteteste", "email": "cliente@example.com",
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
        "password": "minhasenhasegura", "confirm_password": "senhadiferente",
        "accepted_terms_version": "2026-10-31",
    })
    assert response.status_code == 422


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
        "username": "novousuario", "accepted_terms_version": "2026-10-31",
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
        "password": "senhasegura123", "confirm_password": "senhasegura123",
        "accepted_terms_version": "2026-10-31",
    })
    assert result.status_code == 202
    assert result.json()["email_confirmation_required"] is True
    assert captured["options"]["email_redirect_to"] == "https://app.example.com/login"
    assert db.tables["users"] == []
    assert len(db.tables["pending_auth_registrations"]) == 1


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

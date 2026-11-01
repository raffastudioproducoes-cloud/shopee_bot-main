"""Contrato de autenticação Supabase/Auth sem chamadas externas ou gravações reais."""
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
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

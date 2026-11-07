"""Shopee Video Management para criadores afiliados: assinatura, OAuth e isolamento."""

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from api.crypto import decrypt, encrypt
from api.main import app
from api import shopee_video_oauth as oauth
from api.routers import shopee_video
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id
from api.routers import credentials
from api.routers.credentials import _require_admin


def test_affiliate_authorization_is_user_not_seller():
    url = oauth.authorization_url(
        123, "https://example.org/api/shopee-video/callback", "csrf-opaque", sandbox=False,
    )
    parsed = urlsplit(url)
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https" and parsed.netloc == "open.shopee.com.br"
    assert params == {
        "partner_id": ["123"], "auth_type": ["user"],
        "redirect_uri": ["https://example.org/api/shopee-video/callback"],
        "response_type": ["code"], "state": ["csrf-opaque"],
    }
    assert "test-stable" in oauth.authorization_url(123, "https://example.org/cb", "state", sandbox=True)


def test_official_hmac_uses_partner_path_and_timestamp_only():
    expected = hmac.new(
        b"test-partner-key", b"123/api/v2/auth/token/get1700000000", hashlib.sha256,
    ).hexdigest()
    assert oauth.signature(123, "test-partner-key", oauth.TOKEN_PATH, 1700000000) == expected


def test_exchange_code_only_accepts_single_affiliate_user(monkeypatch):
    sent = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "access-123", "refresh_token": "refresh-123", "expire_in": 14400,
                    "user_id_list": [98765]}

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, *, params, json):
            sent.append((url, params, json))
            return Response()

    monkeypatch.setattr(oauth.httpx, "AsyncClient", Client)
    monkeypatch.setattr(oauth.time, "time", lambda: 1700000000)
    result = asyncio.run(oauth.exchange_code(123, "test-partner-key", "authorization-code", sandbox=True))
    assert result["user_id_list"] == [98765]
    url, params, body = sent[0]
    assert url.endswith(oauth.TOKEN_PATH) and "sandbox" in url
    assert body == {"code": "authorization-code", "partner_id": 123}
    assert params["sign"] == oauth.signature(123, "test-partner-key", oauth.TOKEN_PATH, 1700000000)
    assert "test-partner-key" not in str(sent)


@pytest.fixture
def video_db(fake_db, monkeypatch):
    now = datetime.now(timezone.utc)
    db = fake_db({
        "users": [{"id": "owner", "access": "USER"}, {"id": "other", "access": "USER"}],
        "platform_shopee_video_apps": [{
            "environment": "staging", "partner_id": 123,
            "partner_key": encrypt("test-partner-key"), "sandbox": True, "enabled": True,
        }],
        "shopee_video_authorizations": [{
            "environment": "staging", "user_id": "owner", "profile_id": "profile-a",
            "partner_id": 123, "shopee_user_id": 98765,
            "access_token": encrypt("private-access"), "refresh_token": encrypt("private-refresh"),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "refresh_expires_at": (now + timedelta(days=20)).isoformat(),
        }],
        "products": [
            {"user_id": "owner", "profile_id": "profile-a", "product_id": 11},
            {"user_id": "owner", "profile_id": "profile-b", "product_id": 22},
            {"user_id": "other", "profile_id": "profile-a", "product_id": 33},
        ],
    })
    monkeypatch.setattr(shopee_video, "supabase", db)
    monkeypatch.setattr(credentials, "supabase", db)
    monkeypatch.setattr(shopee_video, "current_environment", lambda: "staging")
    monkeypatch.setattr(shopee_video, "log_action", lambda *_, **__: None)
    monkeypatch.setenv("SHOPEE_VIDEO_CALLBACK_URL", "https://example.org/api/shopee-video/callback")
    yield db
    app.dependency_overrides.clear()


def as_profile(user_id="owner", profile_id="profile-a", admin=False):
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_current_profile_id] = lambda: profile_id
    if admin:
        app.dependency_overrides[_require_admin] = lambda: user_id
    # Cookie de state é Secure; simular HTTPS, como no Render real.
    return TestClient(app, base_url="https://testserver")


def test_user_status_never_exposes_global_or_personal_keys(video_db):
    with as_profile() as client:
        response = client.get("/shopee-video/status")
        assert response.status_code == 200
        assert response.json() == {"configured": True, "connected": True, "token_valid": True,
                                   "sandbox": True, "publishing_enabled": False}
        for secret in ("private-access", "private-refresh", "test-partner-key"):
            assert secret not in response.text
    with as_profile(profile_id="profile-b") as client:
        assert client.get("/shopee-video/status").json()["connected"] is False
    with as_profile(user_id="other") as client:
        assert client.get("/shopee-video/status").json()["connected"] is False


def test_user_cannot_configure_global_app(video_db):
    with as_profile() as client:
        assert client.get("/admin/shopee-video").status_code in (401, 403)
        assert client.put("/admin/shopee-video", json={
            "partner_id": 999, "partner_key": "attacker-secret", "sandbox": False,
        }).status_code in (401, 403)
    assert decrypt(video_db.tables["platform_shopee_video_apps"][0]["partner_key"]) == "test-partner-key"


def test_oauth_callback_binds_csrf_and_profile(video_db, monkeypatch):
    async def exchange(*_args, **_kwargs):
        return {"user_id_list": [123456], "access_token": "new-access",
                "refresh_token": "new-refresh", "expire_in": 14400}

    monkeypatch.setattr(oauth, "exchange_code", exchange)
    with as_profile(user_id="other", profile_id="profile-b") as client:
        init = client.get("/shopee-video/authorize")
        assert init.status_code == 200
        params = parse_qs(urlsplit(init.json()["url"]).query)
        assert params["auth_type"] == ["user"]
        state = params["state"][0]
        assert client.get(f"/shopee-video/callback?code=okay&state={state}-tampered",
                          follow_redirects=False).headers["location"].endswith("shopee_video=error")
        # Falha de CSRF descarta o cookie: iniciar um novo consentimento.
        retried = client.get("/shopee-video/authorize")
        state = parse_qs(urlsplit(retried.json()["url"]).query)["state"][0]
        assert client.get(f"/shopee-video/callback?code=okay&state={state}",
                          follow_redirects=False).headers["location"].endswith("shopee_video=success")
    rows = [r for r in video_db.tables["shopee_video_authorizations"] if r["user_id"] == "other"]
    assert len(rows) == 1 and rows[0]["profile_id"] == "profile-b"
    assert decrypt(rows[0]["access_token"]) == "new-access"
    assert decrypt(rows[0]["refresh_token"]) == "new-refresh"
    assert decrypt(video_db.tables["shopee_video_authorizations"][0]["access_token"]) == "private-access"
def test_refresh_is_restricted_to_own_profile(video_db, monkeypatch):
    received = []

    async def refresh(*args, **kwargs):
        received.append((args, kwargs))
        return {"access_token": "renewed-access", "refresh_token": "renewed-refresh", "expire_in": 14400}

    monkeypatch.setattr(oauth, "refresh_token", refresh)
    with as_profile(profile_id="profile-b") as client:
        assert client.post("/shopee-video/refresh").status_code == 409
    with as_profile() as client:
        response = client.post("/shopee-video/refresh")
        assert response.status_code == 200, response.text
        assert response.json() == {"connected": True, "token_valid": True}
    assert len(received) == 1 and received[0][0][2:4] == (98765, "private-refresh")
    assert decrypt(video_db.tables["shopee_video_authorizations"][0]["access_token"]) == "renewed-access"


def test_preview_verifies_owner_products_without_publishing(video_db):
    body = {"caption": "Produto do dia", "product_item_ids": [11], "video_seconds": 20,
            "video_bytes": 1_000_000, "aigc_label": False}
    with as_profile() as client:
        response = client.post("/shopee-video/preview", json=body)
        assert response.status_code == 200 and response.json()["publication"] == "não enviada"
        assert client.post("/shopee-video/preview", json={**body, "product_item_ids": [22]}).status_code == 422
        assert client.post("/shopee-video/preview", json={**body, "product_item_ids": [33]}).status_code == 422
        assert client.post("/shopee-video/preview", json={**body, "product_item_ids": [11, 11]}).status_code == 422
        assert client.post("/shopee-video/preview", json={**body, "caption": "x" * 151}).status_code == 422
    assert decrypt(video_db.tables["shopee_video_authorizations"][0]["access_token"]) == "private-access"


"""Token válido/renovável da Shopee Vídeo: renova, não renova, falha → reconexão."""

from datetime import datetime, timedelta, timezone

import pytest

from api import shopee_video_oauth as oauth
from api import shopee_video_tokens as tokens
from api.crypto import decrypt, encrypt

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def _auth(**overrides):
    row = {
        "environment": "staging", "user_id": "owner", "profile_id": "profile-a",
        "partner_id": 123, "shopee_user_id": 98765,
        "access_token": encrypt("old-access"), "refresh_token": encrypt("old-refresh"),
        "expires_at": (NOW + timedelta(hours=2)).isoformat(),
        "refresh_expires_at": (NOW + timedelta(days=20)).isoformat(),
        "needs_reconnect": False,
    }
    row.update(overrides)
    return row


@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "platform_shopee_video_apps": [{
            "environment": "staging", "partner_id": 123,
            "partner_key": encrypt("test-partner-key"), "sandbox": True, "enabled": True,
        }],
        "shopee_video_authorizations": [_auth()],
    })
    monkeypatch.setattr(tokens, "supabase", database)
    monkeypatch.setattr(tokens, "current_environment", lambda: "staging")
    return database


def _row(db):
    return db.tables["shopee_video_authorizations"][0]


def _refresh_ok(calls):
    def refresh(partner_id, partner_key, user_id, refresh, *, sandbox):
        calls.append((partner_id, partner_key, user_id, refresh, sandbox))
        return {"access_token": "new-access", "refresh_token": "new-refresh", "expire_in": 14400}
    return refresh


def test_valid_token_is_returned_without_refresh(db, monkeypatch):
    calls = []
    monkeypatch.setattr(oauth, "refresh_token_sync", _refresh_ok(calls))
    auth = tokens.get_valid_authorization("owner", "profile-a", now=NOW)
    assert (auth.access_token, auth.shopee_user_id, auth.partner_key) == ("old-access", 98765, "test-partner-key")
    assert calls == []


def test_token_near_expiry_is_renewed_and_pair_saved(db, monkeypatch):
    _row(db)["expires_at"] = (NOW + timedelta(minutes=9)).isoformat()
    calls = []
    monkeypatch.setattr(oauth, "refresh_token_sync", _refresh_ok(calls))
    auth = tokens.get_valid_authorization("owner", "profile-a", now=NOW)
    assert auth.access_token == "new-access"
    assert calls == [(123, "test-partner-key", 98765, "old-refresh", True)]
    row = _row(db)
    assert decrypt(row["access_token"]) == "new-access" and decrypt(row["refresh_token"]) == "new-refresh"
    assert row["refresh_expires_at"] == (NOW + timedelta(days=30)).isoformat()


def test_rejected_refresh_marks_needs_reconnect(db, monkeypatch, caplog):
    _row(db)["expires_at"] = (NOW - timedelta(minutes=1)).isoformat()

    def rejected(*_a, **_k):
        raise oauth.ShopeeVideoRefreshRejected("x")

    monkeypatch.setattr(oauth, "refresh_token_sync", rejected)
    with pytest.raises(tokens.ShopeeVideoReconnectRequired, match="reconecte"):
        tokens.get_valid_authorization("owner", "profile-a", now=NOW)
    assert _row(db)["needs_reconnect"] is True
    assert "old-refresh" not in caplog.text and "old-access" not in caplog.text


def test_failed_write_after_refresh_marks_needs_reconnect(db, monkeypatch, caplog):
    _row(db)["expires_at"] = (NOW - timedelta(minutes=1)).isoformat()
    monkeypatch.setattr(oauth, "refresh_token_sync", _refresh_ok([]))
    def broken(*args, **kwargs):
        raise RuntimeError("supabase fora")

    monkeypatch.setattr(tokens, "_store_refreshed", broken)
    with pytest.raises(tokens.ShopeeVideoReconnectRequired):
        tokens.get_valid_authorization("owner", "profile-a", now=NOW)
    assert _row(db)["needs_reconnect"] is True
    assert "new-refresh" not in caplog.text


def test_transient_refresh_error_does_not_mark_reconnect(db, monkeypatch):
    _row(db)["expires_at"] = (NOW - timedelta(minutes=1)).isoformat()

    def down(*_a, **_k):
        raise oauth.ShopeeVideoOAuthError("rede")

    monkeypatch.setattr(oauth, "refresh_token_sync", down)
    with pytest.raises(oauth.ShopeeVideoOAuthError):
        tokens.get_valid_authorization("owner", "profile-a", now=NOW)
    assert _row(db)["needs_reconnect"] is False


def test_marked_or_missing_authorization_never_calls_shopee(db, monkeypatch):
    monkeypatch.setattr(oauth, "refresh_token_sync", lambda *a, **k: pytest.fail("não deve renovar"))
    _row(db)["needs_reconnect"] = True
    with pytest.raises(tokens.ShopeeVideoReconnectRequired):
        tokens.get_valid_authorization("owner", "profile-a", now=NOW)
    with pytest.raises(tokens.ShopeeVideoNotConfigured):
        tokens.get_valid_authorization("owner", "profile-b", now=NOW)
    db.tables["platform_shopee_video_apps"][0]["enabled"] = False
    with pytest.raises(tokens.ShopeeVideoNotConfigured):
        tokens.get_valid_authorization("owner", "profile-a", now=NOW)


def test_connection_state_flags(db):
    state = tokens.connection_state("owner", "profile-a", now=NOW)
    assert state == {"configured": True, "connected": True, "token_valid": True,
                     "needs_reconnect": False, "sandbox": True, "publishing_enabled": True}
    _row(db)["expires_at"] = (NOW - timedelta(minutes=1)).isoformat()
    renewable = tokens.connection_state("owner", "profile-a", now=NOW)
    assert renewable["token_valid"] is False and renewable["publishing_enabled"] is True
    _row(db)["needs_reconnect"] = True
    marked = tokens.connection_state("owner", "profile-a", now=NOW)
    assert marked["needs_reconnect"] is True and marked["publishing_enabled"] is False
    assert tokens.connection_state("owner", "profile-b", now=NOW)["connected"] is False


def test_refresh_job_renews_only_expiring_rows(db, monkeypatch, caplog):
    rows = db.tables["shopee_video_authorizations"]
    rows[0]["expires_at"] = (NOW + timedelta(minutes=30)).isoformat()  # access < 1 h
    rows.append(_auth(profile_id="profile-b", refresh_token=encrypt("b-refresh"),
                      refresh_expires_at=(NOW + timedelta(days=3)).isoformat()))  # refresh < 5 dias
    rows.append(_auth(profile_id="profile-c", refresh_token=encrypt("c-refresh")))  # folgado
    rows.append(_auth(profile_id="profile-d", needs_reconnect=True,
                      expires_at=(NOW - timedelta(hours=1)).isoformat()))
    calls = []
    monkeypatch.setattr(oauth, "refresh_token_sync", _refresh_ok(calls))

    assert tokens.refresh_expiring(NOW) == {"refreshed": 2, "reconnect": 0, "errors": 0}
    assert sorted(c[3] for c in calls) == ["b-refresh", "old-refresh"]
    assert decrypt(rows[2]["refresh_token"]) == "c-refresh"
    assert "new-access" not in caplog.text


def test_refresh_job_is_noop_without_app(db, monkeypatch):
    db.tables["platform_shopee_video_apps"].clear()
    monkeypatch.setattr(oauth, "refresh_token_sync", lambda *a, **k: pytest.fail("não deve renovar"))
    assert tokens.refresh_expiring(NOW) == {"refreshed": 0, "reconnect": 0, "errors": 0}


def test_oauth_refresh_rejection_vs_transient(monkeypatch):
    class Response:
        def __init__(self, payload, status=200):
            self.payload, self.status_code = payload, status

        def json(self):
            return self.payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise oauth.httpx.HTTPStatusError("x", request=None, response=None)

    class Client:
        reply = None

        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def post(self, url, *, params, json):
            assert url == "https://partner.test-stable.shopeemobile.com" + oauth.REFRESH_PATH
            return Client.reply

    monkeypatch.delenv("SHOPEE_VIDEO_SANDBOX_API_BASE_URL", raising=False)
    monkeypatch.setattr(oauth.httpx, "Client", Client)
    Client.reply = Response({"error": "error_auth", "message": "invalid refresh_token"}, 403)
    with pytest.raises(oauth.ShopeeVideoRefreshRejected):
        oauth.refresh_token_sync(1, "k", 2, "r", sandbox=True)
    Client.reply = Response({"error": "error_server"}, 500)
    with pytest.raises(oauth.ShopeeVideoOAuthError) as exc:
        oauth.refresh_token_sync(1, "k", 2, "r", sandbox=True)
    assert not isinstance(exc.value, oauth.ShopeeVideoRefreshRejected)
    Client.reply = Response({"access_token": "a", "refresh_token": "b", "expire_in": 14400})
    assert oauth.refresh_token_sync(1, "k", 2, "r", sandbox=True)["refresh_token"] == "b"

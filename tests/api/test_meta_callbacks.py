import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.main import app
from api.routers import auth as auth_module
from api.routers import meta_callbacks


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    auth_module._login_attempts.clear()
    return TestClient(app)


@pytest.fixture
def db(fake_db, monkeypatch):
    database = fake_db({
        "facebook_credentials": [],
        "instagram_credentials": [],
        "threads_credentials": [],
        "credential_checks": [],
        "data_deletion_requests": [],
        "audit_events": [],
    })
    monkeypatch.setattr(meta_callbacks, "supabase", database)
    monkeypatch.setattr(meta_callbacks, "record_audit_event", lambda *a, **kw: None)
    monkeypatch.setattr(meta_callbacks, "log_action", lambda *a, **kw: None)
    monkeypatch.setattr(meta_callbacks.instagram_oauth, "SECRET", "meta-secret")
    monkeypatch.setattr(meta_callbacks.threads_oauth, "SECRET", "threads-secret")
    monkeypatch.setattr(settings, "frontend_url", "https://shopee-bot-fj0w.onrender.com")
    meta_callbacks._rate_attempts.clear()
    meta_callbacks._replay_cache.clear()
    return database


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _signed(payload: dict, secret: str) -> str:
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return f"{_b64url(sig)}.{payload_b64}"


def _payload(user_id="external-1", issued_at=None):
    return {
        "algorithm": "HMAC-SHA256",
        "user_id": user_id,
        "issued_at": int(time.time()) if issued_at is None else issued_at,
    }


def _post(client, path, signed_request):
    return client.post(
        path,
        data={"signed_request": signed_request},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )


def test_meta_deauthorize_valid_signature_disconnects_only_matching_external_id(client, db):
    db.tables["instagram_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "fb_user_id": "fb-a",
            "ig_user_id": "ig-a",
            "user_access_token": "tok-a",
            "status": True,
        },
        {
            "id": 2,
            "user_id": "user-b",
            "profile_id": "profile-b",
            "fb_user_id": "fb-b",
            "ig_user_id": "ig-b",
            "user_access_token": "tok-b",
            "status": True,
        },
    ]
    db.tables["credential_checks"] = [
        {"id": 10, "user_id": "user-a", "profile_id": "profile-a", "network": "instagram"},
        {"id": 11, "user_id": "user-b", "profile_id": "profile-b", "network": "instagram"},
    ]

    res = _post(client, "/meta/deauthorize", _signed(_payload("fb-a"), "meta-secret"))

    assert res.status_code == 200
    assert res.json() == {"status": "received"}
    assert db.tables["instagram_credentials"][0]["user_access_token"] is None
    assert db.tables["instagram_credentials"][0]["ig_user_id"] == "ig-a"
    assert db.tables["instagram_credentials"][0]["fb_user_id"] == "fb-a"
    assert db.tables["instagram_credentials"][0]["status"] is False
    assert db.tables["instagram_credentials"][1]["user_access_token"] == "tok-b"
    assert [c["id"] for c in db.tables["credential_checks"]] == [11]


def test_meta_deauthorize_does_not_match_instagram_ig_user_id(client, db):
    db.tables["instagram_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "ig_user_id": "ig-legacy",
            "user_access_token": "tok-a",
            "status": True,
        }
    ]

    res = _post(client, "/meta/deauthorize", _signed(_payload("ig-legacy"), "meta-secret"))

    assert res.status_code == 200
    assert db.tables["instagram_credentials"][0]["user_access_token"] == "tok-a"
    assert db.tables["instagram_credentials"][0]["ig_user_id"] == "ig-legacy"


@pytest.mark.parametrize(
    "signed_request",
    [
        "malformed",
        "bad.signature.parts",
        _signed({"algorithm": "PLAINTEXT", "user_id": "ig-a"}, "meta-secret"),
        _signed({"algorithm": "HMAC-SHA256"}, "meta-secret"),
    ],
)
def test_meta_deauthorize_rejects_malformed_signed_request_without_echo(client, db, signed_request):
    res = _post(client, "/meta/deauthorize", signed_request)

    assert res.status_code == 400
    assert signed_request not in res.text


def test_meta_deauthorize_rejects_invalid_signature_without_echo(client, db):
    leak = _signed(_payload("leak-user-id"), "wrong-secret")

    res = _post(client, "/meta/deauthorize", leak)

    assert res.status_code == 400
    assert "leak-user-id" not in res.text
    assert leak not in res.text


def test_missing_app_secret_fails_closed_without_mutation(client, db, monkeypatch):
    monkeypatch.setattr(meta_callbacks.instagram_oauth, "SECRET", None)
    db.tables["instagram_credentials"] = [
        {"id": 1, "ig_user_id": "ig-a", "user_access_token": "tok", "status": True}
    ]

    res = _post(client, "/meta/deauthorize", _signed(_payload("ig-a"), "meta-secret"))

    assert res.status_code == 503
    assert db.tables["instagram_credentials"][0]["user_access_token"] == "tok"


def test_unknown_user_data_deletion_returns_same_shape_and_not_found_status(client, db):
    res = _post(client, "/meta/data-deletion", _signed(_payload("missing"), "meta-secret"))

    assert res.status_code == 200
    body = res.json()
    assert list(body) == ["url", "confirmation_code"]
    assert body["url"].startswith(
        "https://shopee-bot-fj0w.onrender.com/api/meta/data-deletion/status?code="
    )

    status = client.get("/meta/data-deletion/status", params={"code": body["confirmation_code"]})
    assert status.status_code == 200
    assert status.json()["status"] == "not_found"
    assert status.json()["provider"] == "meta"


def test_data_deletion_is_idempotent_and_removes_network_data(client, db):
    db.tables["facebook_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "app_id": "old-app",
            "secret": "old-secret",
            "fb_user_id": "fb-user-a",
            "page_id": "page-a",
            "page_name": "Page A",
            "page_access_token": "tok",
            "status": True,
        }
    ]
    signed_request = _signed(_payload("fb-user-a"), "meta-secret")

    first = _post(client, "/meta/data-deletion", signed_request)
    second = _post(client, "/meta/data-deletion", signed_request)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(db.tables["data_deletion_requests"]) == 1
    assert db.tables["data_deletion_requests"][0]["status"] == "completed"
    assert db.tables["data_deletion_requests"][0]["external_user_hash"] != "fb-user-a"
    assert db.tables["facebook_credentials"][0]["app_id"] is None
    assert db.tables["facebook_credentials"][0]["secret"] is None
    assert db.tables["facebook_credentials"][0]["fb_user_id"] is None
    assert db.tables["facebook_credentials"][0]["page_id"] is None
    assert db.tables["facebook_credentials"][0]["page_name"] is None
    assert db.tables["facebook_credentials"][0]["page_access_token"] is None
    assert db.tables["facebook_credentials"][0]["status"] is False


def test_existing_completed_receipt_still_reprocesses_new_connection(client, db):
    hash_value = meta_callbacks._external_hash("meta", "fb-user-a")
    db.tables["data_deletion_requests"] = [
        {
            "id": 7,
            "confirmation_code": "same-code",
            "provider": "meta",
            "external_user_hash": hash_value,
            "status": "completed",
            "completed_at": "2026-10-13T00:00:00+00:00",
        }
    ]
    db.tables["facebook_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "fb_user_id": "fb-user-a",
            "page_id": "page-new",
            "page_name": "New Page",
            "page_access_token": "new-token",
            "status": True,
        }
    ]

    res = _post(client, "/meta/data-deletion", _signed(_payload("fb-user-a"), "meta-secret"))

    assert res.status_code == 200
    assert res.json()["confirmation_code"] == "same-code"
    assert db.tables["facebook_credentials"][0]["fb_user_id"] is None
    assert db.tables["facebook_credentials"][0]["page_access_token"] is None
    assert db.tables["data_deletion_requests"][0]["status"] == "completed"


def test_legacy_facebook_without_fb_user_id_records_honest_not_found(client, db):
    db.tables["facebook_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "page_id": "page-a",
            "page_access_token": "tok",
            "status": True,
        }
    ]

    res = _post(client, "/meta/data-deletion", _signed(_payload("fb-user-a"), "meta-secret"))

    assert res.status_code == 200
    assert db.tables["data_deletion_requests"][0]["status"] == "not_found"
    assert db.tables["facebook_credentials"][0]["page_access_token"] == "tok"


def test_deletion_receipt_is_received_before_cleanup_failure(db, monkeypatch):
    app.dependency_overrides.clear()
    client = TestClient(app, raise_server_exceptions=False)

    def fail_cleanup(*_args, **_kwargs):
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(meta_callbacks, "_disconnect_by_external_id", fail_cleanup)

    res = _post(client, "/meta/data-deletion", _signed(_payload("fb-user-a"), "meta-secret"))

    assert res.status_code == 500
    assert len(db.tables["data_deletion_requests"]) == 1
    assert db.tables["data_deletion_requests"][0]["status"] == "received"
    assert db.tables["data_deletion_requests"][0]["completed_at"] is None


@pytest.mark.parametrize("failing_step", ["credential_checks", "audit"])
def test_meta_data_deletion_retry_after_partial_failure_stays_completed_not_not_found(
    db, monkeypatch, failing_step
):
    app.dependency_overrides.clear()
    client = TestClient(app, raise_server_exceptions=False)
    db.tables["instagram_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "fb_user_id": "fb-user-a",
            "ig_user_id": "ig-user-a",
            "user_access_token": "tok-a",
            "status": True,
        }
    ]
    signed_request = _signed(_payload("fb-user-a"), "meta-secret")
    calls = {"credential_checks": 0, "audit": 0}
    original_delete_checks = meta_callbacks._delete_credential_checks

    def maybe_fail_delete_checks(rows, network):
        calls["credential_checks"] += 1
        if failing_step == "credential_checks" and calls["credential_checks"] == 1:
            raise RuntimeError("injected credential_checks failure")
        return original_delete_checks(rows, network)

    def maybe_fail_audit(*_args, **_kwargs):
        calls["audit"] += 1
        if failing_step == "audit" and calls["audit"] == 1:
            raise RuntimeError("injected audit failure")

    monkeypatch.setattr(meta_callbacks, "_delete_credential_checks", maybe_fail_delete_checks)
    monkeypatch.setattr(meta_callbacks, "record_audit_event", maybe_fail_audit)

    first = _post(client, "/meta/data-deletion", signed_request)
    second = _post(client, "/meta/data-deletion", signed_request)

    assert first.status_code == 500
    assert second.status_code == 200
    assert db.tables["data_deletion_requests"][0]["status"] == "completed"
    assert db.tables["data_deletion_requests"][0]["status"] != "not_found"
    assert db.tables["instagram_credentials"][0]["fb_user_id"] is None
    assert db.tables["instagram_credentials"][0]["ig_user_id"] is None


def test_confirmation_code_is_unique_per_external_user(client, db):
    first = _post(client, "/meta/data-deletion", _signed(_payload("one"), "meta-secret"))
    second = _post(client, "/meta/data-deletion", _signed(_payload("two"), "meta-secret"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["confirmation_code"] != second.json()["confirmation_code"]


def test_threads_uses_threads_secret_not_meta_secret(client, db):
    db.tables["threads_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "t_user_id": "thread-a",
            "access_token": "tok",
            "status": True,
        }
    ]

    wrong = _post(client, "/threads/uninstall", _signed(_payload("thread-a"), "meta-secret"))
    right = _post(client, "/threads/uninstall", _signed(_payload("thread-a"), "threads-secret"))

    assert wrong.status_code == 400
    assert right.status_code == 200
    assert db.tables["threads_credentials"][0]["access_token"] is None
    assert db.tables["threads_credentials"][0]["t_user_id"] == "thread-a"


def test_threads_delete_records_public_status(client, db):
    db.tables["threads_credentials"] = [
        {
            "id": 1,
            "user_id": "user-a",
            "profile_id": "profile-a",
            "t_user_id": "thread-a",
            "access_token": "tok",
            "status": True,
        }
    ]

    res = _post(client, "/threads/delete", _signed(_payload("thread-a"), "threads-secret"))

    assert res.status_code == 200
    code = res.json()["confirmation_code"]
    status = client.get("/meta/data-deletion/status", params={"code": code})
    assert status.status_code == 200
    assert status.json()["provider"] == "threads"
    assert status.json()["status"] == "completed"
    assert db.tables["threads_credentials"][0]["t_user_id"] is None
    assert db.tables["threads_credentials"][0]["access_token"] is None


def test_old_issued_at_signed_request_is_rejected(client, db):
    old_payload = {"algorithm": "HMAC-SHA256", "user_id": "fb-user-a", "issued_at": 1}

    res = _post(client, "/meta/data-deletion", _signed(old_payload, "meta-secret"))

    assert res.status_code == 400
    assert db.tables["data_deletion_requests"] == []


def test_invalid_signature_rate_limit_does_not_count_valid_callbacks(client, db, monkeypatch):
    monkeypatch.setattr(meta_callbacks, "_INVALID_SIGNATURE_LIMIT", 1)
    bad = _signed(_payload("fb-user-a"), "wrong-secret")
    good = _signed(_payload("fb-user-a"), "meta-secret")

    assert _post(client, "/meta/data-deletion", bad).status_code == 400
    assert _post(client, "/meta/data-deletion", good).status_code == 200
    assert _post(client, "/meta/data-deletion", bad).status_code == 429


def test_status_endpoint_has_own_light_rate_limit(client, db, monkeypatch):
    monkeypatch.setattr(meta_callbacks, "_STATUS_LIMIT", 1)
    db.tables["data_deletion_requests"] = [
        {
            "id": 1,
            "confirmation_code": "code-1",
            "provider": "meta",
            "status": "completed",
            "created_at": "2026-10-13T00:00:00+00:00",
            "completed_at": "2026-10-13T00:00:01+00:00",
        }
    ]

    assert client.get("/meta/data-deletion/status", params={"code": "code-1"}).status_code == 200
    assert client.get("/meta/data-deletion/status", params={"code": "code-1"}).status_code == 429


def test_large_body_is_rejected(client, db):
    res = client.post(
        "/meta/deauthorize",
        content=b"signed_request=" + (b"x" * 5000),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert res.status_code == 413


# ── F-01: replay de signed_request ───────────────────────────────────────────


def _connected_instagram(**extra):
    return {
        "id": 1,
        "user_id": "user-a",
        "profile_id": "profile-a",
        "fb_user_id": "fb-a",
        "user_access_token": "tok-a",
        "status": True,
        **extra,
    }


def test_signed_request_without_issued_at_is_rejected(client, db):
    db.tables["instagram_credentials"] = [_connected_instagram()]
    payload = {"algorithm": "HMAC-SHA256", "user_id": "fb-a"}

    res = _post(client, "/meta/deauthorize", _signed(payload, "meta-secret"))

    assert res.status_code == 400
    assert db.tables["instagram_credentials"][0]["status"] is True


@pytest.mark.parametrize("offset", [-2 * 3600, 3600])
def test_signed_request_outside_window_is_rejected(client, db, offset):
    db.tables["instagram_credentials"] = [_connected_instagram()]
    payload = _payload("fb-a", issued_at=int(time.time()) + offset)

    res = _post(client, "/meta/deauthorize", _signed(payload, "meta-secret"))

    assert res.status_code == 400
    assert db.tables["instagram_credentials"][0]["status"] is True


def test_replayed_deauthorize_is_idempotent_and_does_not_reprocess(client, db):
    db.tables["instagram_credentials"] = [_connected_instagram()]
    signed_request = _signed(_payload("fb-a"), "meta-secret")

    first = _post(client, "/meta/deauthorize", signed_request)
    assert db.tables["instagram_credentials"][0]["status"] is False
    # usuario reconecta; o mesmo payload capturado nao pode desconectar de novo
    db.tables["instagram_credentials"][0].update(status=True, user_access_token="new")
    second = _post(client, "/meta/deauthorize", signed_request)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db.tables["instagram_credentials"][0]["status"] is True
    assert db.tables["instagram_credentials"][0]["user_access_token"] == "new"


def test_replayed_data_deletion_returns_same_code_without_reprocessing(client, db):
    db.tables["instagram_credentials"] = [_connected_instagram()]
    signed_request = _signed(_payload("fb-a"), "meta-secret")

    first = _post(client, "/meta/data-deletion", signed_request)
    db.tables["instagram_credentials"][0].update(fb_user_id="fb-a", status=True)
    second = _post(client, "/meta/data-deletion", signed_request)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db.tables["instagram_credentials"][0]["status"] is True
    assert len(db.tables["data_deletion_requests"]) == 1


def test_new_signed_request_for_same_user_is_processed_again(client, db):
    db.tables["instagram_credentials"] = [_connected_instagram()]
    now = int(time.time())

    _post(client, "/meta/deauthorize", _signed(_payload("fb-a", now - 10), "meta-secret"))
    db.tables["instagram_credentials"][0].update(status=True)
    res = _post(client, "/meta/deauthorize", _signed(_payload("fb-a", now), "meta-secret"))

    assert res.status_code == 200
    assert db.tables["instagram_credentials"][0]["status"] is False


def test_replay_cache_expires_and_is_bounded(monkeypatch):
    monkeypatch.setattr(meta_callbacks, "_REPLAY_MAX_KEYS", 2)
    meta_callbacks._replay_cache.clear()
    for i in range(3):
        meta_callbacks._remember_replay(("e", f"u{i}", 1), {"i": i})
    assert len(meta_callbacks._replay_cache) <= 2
    future = time.time() + 10**6
    monkeypatch.setattr(meta_callbacks.time, "time", lambda: future)
    assert meta_callbacks._recall_replay(("e", "u2", 1)) is None


# ── F-03: codigo de exclusao em query string ─────────────────────────────────


def test_status_response_forbids_referrer_and_caching(client, db):
    db.tables["data_deletion_requests"] = [
        {"id": 1, "confirmation_code": "code-1", "provider": "meta", "status": "completed",
         "created_at": "2026-10-13T00:00:00+00:00", "completed_at": None}
    ]

    res = client.get("/meta/data-deletion/status", params={"code": "code-1"})

    assert res.headers["referrer-policy"] == "no-referrer"
    assert "no-store" in res.headers["cache-control"]


def test_every_response_sends_no_referrer(client):
    assert client.get("/health").headers["referrer-policy"] == "no-referrer"


def test_access_log_never_contains_confirmation_code():
    import logging

    from api.middleware import AccessLogRedactor

    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 0,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1", "GET", "/meta/data-deletion/status?code=SEGREDO123&x=1", "1.1", 200), None,
    )

    assert AccessLogRedactor().filter(record) is True
    assert "SEGREDO123" not in record.getMessage()
    assert "/meta/data-deletion/status" in record.getMessage()


def test_access_log_redactor_is_installed_on_uvicorn_access():
    import logging

    from api import main  # noqa: F401
    from api.middleware import AccessLogRedactor

    assert any(isinstance(f, AccessLogRedactor) for f in logging.getLogger("uvicorn.access").filters)


def test_confirmation_code_is_opaque(client, db):
    res = _post(client, "/meta/data-deletion", _signed(_payload("fb-user-a"), "meta-secret"))

    code = res.json()["confirmation_code"]
    assert len(code) >= 32
    assert "fb-user-a" not in code and "fb-user-a" not in res.json()["url"]

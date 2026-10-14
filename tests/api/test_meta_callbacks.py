import base64
import hashlib
import hmac
import json

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
    return database


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _signed(payload: dict, secret: str) -> str:
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return f"{_b64url(sig)}.{payload_b64}"


def _payload(user_id="external-1"):
    return {"algorithm": "HMAC-SHA256", "user_id": user_id}


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
            "ig_user_id": "ig-a",
            "user_access_token": "tok-a",
            "status": True,
        },
        {
            "id": 2,
            "user_id": "user-b",
            "profile_id": "profile-b",
            "ig_user_id": "ig-b",
            "user_access_token": "tok-b",
            "status": True,
        },
    ]
    db.tables["credential_checks"] = [
        {"id": 10, "user_id": "user-a", "profile_id": "profile-a", "network": "instagram"},
        {"id": 11, "user_id": "user-b", "profile_id": "profile-b", "network": "instagram"},
    ]

    res = _post(client, "/meta/deauthorize", _signed(_payload("ig-a"), "meta-secret"))

    assert res.status_code == 200
    assert res.json() == {"status": "received"}
    assert db.tables["instagram_credentials"][0]["user_access_token"] is None
    assert db.tables["instagram_credentials"][0]["ig_user_id"] == "ig-a"
    assert db.tables["instagram_credentials"][0]["status"] is False
    assert db.tables["instagram_credentials"][1]["user_access_token"] == "tok-b"
    assert [c["id"] for c in db.tables["credential_checks"]] == [11]


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
            "page_id": "page-a",
            "page_name": "Page A",
            "page_access_token": "tok",
            "status": True,
        }
    ]
    signed_request = _signed(_payload("page-a"), "meta-secret")

    first = _post(client, "/meta/data-deletion", signed_request)
    second = _post(client, "/meta/data-deletion", signed_request)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(db.tables["data_deletion_requests"]) == 1
    assert db.tables["data_deletion_requests"][0]["external_user_hash"] != "page-a"
    assert db.tables["facebook_credentials"][0]["page_id"] is None
    assert db.tables["facebook_credentials"][0]["page_name"] is None
    assert db.tables["facebook_credentials"][0]["page_access_token"] is None
    assert db.tables["facebook_credentials"][0]["status"] is False


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


def test_large_body_is_rejected(client, db):
    res = client.post(
        "/meta/deauthorize",
        content=b"signed_request=" + (b"x" * 5000),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert res.status_code == 413

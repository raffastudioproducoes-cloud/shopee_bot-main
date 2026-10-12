"""Multi-perfil: credenciais são isoladas por perfil ativo; sem perfil, por user_id."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import credentials as credentials_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def client_factory():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    yield lambda: TestClient(app)
    app.dependency_overrides.clear()


def _db(fake_db, monkeypatch, access="USER"):
    db = fake_db({
        "users": [{"id": 42, "access": access}],
        "threads_credentials": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "status": True, "access_token": "tok-a"},
        ],
        "credential_checks": [],
    })
    monkeypatch.setattr(credentials_module, "supabase", db)
    return db


def test_list_shows_only_active_profile_credentials(fake_db, monkeypatch, client_factory, profile_cookie):
    _db(fake_db, monkeypatch)
    a = client_factory()
    a.cookies.update(profile_cookie("profile-a"))
    b = client_factory()
    b.cookies.update(profile_cookie("profile-b"))

    assert a.get("/credentials").json()["threads"]["connected"] is True
    assert b.get("/credentials").json()["threads"]["connected"] is False


def test_list_without_profile_falls_back_to_user_scope(
    fake_db, monkeypatch, client_factory, old_token_without_profile_claim
):
    _db(fake_db, monkeypatch)
    c = client_factory()
    c.cookies.update(old_token_without_profile_claim)
    assert c.get("/credentials").json()["threads"]["connected"] is True


def test_save_writes_profile_id_and_does_not_touch_other_profile(
    fake_db, monkeypatch, client_factory, profile_cookie
):
    db = _db(fake_db, monkeypatch, access="ADMIN")
    b = client_factory()
    b.cookies.update(profile_cookie("profile-b"))

    res = b.put("/credentials/threads", json={"t_user_id": "9", "access_token": "tok-b"})

    assert res.status_code == 200
    rows = db.tables["threads_credentials"]
    assert len(rows) == 2
    assert rows[0]["access_token"] == "tok-a" and rows[0]["profile_id"] == "profile-a"
    assert rows[1]["profile_id"] == "profile-b" and rows[1]["t_user_id"] == "9"


def test_regular_user_cannot_save_a_manual_threads_override(
    fake_db, monkeypatch, client_factory, profile_cookie
):
    db = _db(fake_db, monkeypatch)
    client = client_factory()
    client.cookies.update(profile_cookie("profile-b"))

    response = client.put("/credentials/threads", json={"t_user_id": "9", "access_token": "tok-b"})

    assert response.status_code == 403
    assert len(db.tables["threads_credentials"]) == 1


def test_delete_other_profile_credential_returns_404_and_keeps_data(
    fake_db, monkeypatch, client_factory, profile_cookie
):
    db = _db(fake_db, monkeypatch)
    b = client_factory()
    b.cookies.update(profile_cookie("profile-b"))

    assert b.delete("/credentials/threads").status_code == 404
    assert db.tables["threads_credentials"][0]["status"] is True


def test_test_payload_reads_active_profile_credential_only(fake_db, monkeypatch):
    _db(fake_db, monkeypatch)
    assert credentials_module._test_payload("threads", 42, "profile-b") is None
    from api.crypto import encrypt

    credentials_module.supabase.tables["threads_credentials"][0]["access_token"] = encrypt("real")
    assert credentials_module._test_payload("threads", 42, "profile-a") == {"access_token": "real"}

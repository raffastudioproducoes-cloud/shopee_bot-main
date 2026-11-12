"""Fuso por usuario: validacao IANA, /auth/me, PUT e gravacao na agenda."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import app
from api.routers import auth as auth_module
from api.routers import posts as posts_module
from api import database as database_module
from shopee_bot.utils.timezones import DEFAULT_TIMEZONE, normalize_timezone, timezone_or_default


@pytest.mark.parametrize("name", ["America/Sao_Paulo", "Europe/Lisbon", "Asia/Tokyo", "UTC"])
def test_accepts_iana_names(name):
    assert normalize_timezone(name) == name


@pytest.mark.parametrize("name", ["", "Brasilia", "america/sao_paulo", "../etc/passwd", "X" * 65, None, 3])
def test_rejects_non_iana_values(name):
    with pytest.raises(ValueError):
        normalize_timezone(name)
    assert timezone_or_default(name) == DEFAULT_TIMEZONE


@pytest.fixture(autouse=True)
def _clear_login_rate_limit():
    auth_module._login_attempts.clear()
    yield
    auth_module._login_attempts.clear()


def _login(browser):
    login = browser.post("/auth/login", data={"username": "u", "password": "senha12345"})
    assert login.status_code == 200


@pytest.fixture
def db(fake_db, monkeypatch):
    from passlib.context import CryptContext

    database = fake_db({
        "users": [{
            "id": "u-1", "username": "u", "access": "USER",
            "password": CryptContext(schemes=["bcrypt"], deprecated="auto").hash("senha12345"),
        }],
        "profiles": [{"id": "p-1", "user_id": "u-1", "kind": "principal"}],
        "revoked_sessions": [],
    })
    monkeypatch.setattr(database_module, "get_supabase", lambda: database)
    monkeypatch.setattr(auth_module, "get_supabase", lambda: database)
    app.dependency_overrides.clear()  # outros módulos deixam overrides de autenticação
    return database


def test_me_defaults_to_brasilia_and_unconfirmed_for_old_rows(db):
    with TestClient(app, base_url="https://testserver") as browser:
        _login(browser)
        me = browser.get("/auth/me").json()
    assert me["timezone"] == "America/Sao_Paulo"
    assert me["timezone_confirmed"] is False


def test_put_timezone_saves_valid_name_and_confirms(db):
    with TestClient(app, base_url="https://testserver") as browser:
        _login(browser)
        saved = browser.put("/auth/me/timezone", json={"timezone": "Europe/Lisbon"})
        assert saved.status_code == 200
        assert saved.json() == {"timezone": "Europe/Lisbon", "timezone_confirmed": True}
        me = browser.get("/auth/me").json()
    assert me["timezone"] == "Europe/Lisbon"
    assert me["timezone_confirmed"] is True
    assert db.tables["users"][0]["timezone_updated_at"]


def test_put_timezone_rejects_invalid_name_without_writing(db):
    with TestClient(app, base_url="https://testserver") as browser:
        _login(browser)
        response = browser.put("/auth/me/timezone", json={"timezone": "Mars/Olympus"})
    assert response.status_code == 422
    assert "timezone" not in db.tables["users"][0]


def test_put_timezone_requires_login(db):
    with TestClient(app, base_url="https://testserver") as browser:
        assert browser.put("/auth/me/timezone", json={"timezone": "Asia/Tokyo"}).status_code == 401


def test_schedule_validates_optional_timezone():
    base = {"trigger": "cron", "time": "10:00", "days_of_week": [0]}
    assert posts_module.PostSchedule(**base).timezone is None
    assert posts_module.PostSchedule(**base, timezone="Asia/Tokyo").timezone == "Asia/Tokyo"
    with pytest.raises(ValidationError):
        posts_module.PostSchedule(**base, timezone="GMT-3 Brasilia")


def _capture_jobs(monkeypatch, user_tz):
    sent = []

    async def fake_create(**kwargs):
        sent.append(kwargs)
        return f"job-{len(sent)}"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_create)
    monkeypatch.setattr(posts_module, "_user_timezone", lambda _uid: user_tz)
    return sent


def test_recurring_job_uses_saved_user_timezone(monkeypatch):
    sent = _capture_jobs(monkeypatch, "Europe/Lisbon")
    schedule = posts_module.PostSchedule(trigger="cron", times=["09:00", "18:00"], days_of_week=[0, 2])
    asyncio.run(posts_module._create_schedule_jobs("u-1", 7, "bot_post", schedule, "p-1"))
    assert [job["timezone"] for job in sent] == ["Europe/Lisbon", "Europe/Lisbon"]


def test_recurring_job_prefers_timezone_sent_with_schedule(monkeypatch):
    sent = _capture_jobs(monkeypatch, "Europe/Lisbon")
    schedule = posts_module.PostSchedule(trigger="cron", time="09:00", days_of_week=[0], timezone="Asia/Tokyo")
    asyncio.run(posts_module._create_schedule_jobs("u-1", 7, "bot_post", schedule, "p-1"))
    assert sent[0]["timezone"] == "Asia/Tokyo"


def test_date_job_does_not_send_timezone(monkeypatch):
    sent = _capture_jobs(monkeypatch, "Asia/Tokyo")
    schedule = posts_module.PostSchedule(trigger="date", run_date="2026-12-01T10:00:00")
    asyncio.run(posts_module._create_schedule_jobs("u-1", 7, "bot_post", schedule, "p-1"))
    assert "timezone" not in sent[0]


def test_user_timezone_falls_back_for_missing_row(fake_db, monkeypatch):
    monkeypatch.setattr(posts_module, "supabase", fake_db({"users": []}))
    assert posts_module._user_timezone("ghost") == DEFAULT_TIMEZONE


def test_user_timezone_read_failure_keeps_brasilia(monkeypatch):
    class Broken:
        def table(self, _name):
            raise RuntimeError("offline")

    monkeypatch.setattr(posts_module, "supabase", Broken())
    assert posts_module._user_timezone("u-1") == DEFAULT_TIMEZONE

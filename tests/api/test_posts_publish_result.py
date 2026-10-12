"""
Resultado REAL da publicação no post (`last_result`): o /publish só
dispara o job; o que aconteceu de fato vem das atividades
bot_post_success/failure gravadas pelo scheduler.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id

USER = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def auth_client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: USER
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fake_supabase(activity_rows, recorder=None):
    fake = MagicMock()

    def table(name):
        q = MagicMock()
        for m in ("select", "eq", "is_", "order", "limit", "in_", "maybe_single", "single", "lt"):
            getattr(q, m).return_value = q
        if recorder is not None and name == "activities":
            recorder.append(q)
        if name == "posts":
            q.execute.return_value = MagicMock(data={"id": 7, "user_id": USER, "text": "oi"})
        elif name == "activities":
            q.execute.return_value = MagicMock(data=activity_rows)
        else:
            q.execute.return_value = MagicMock(data=[])
        return q

    fake.table.side_effect = table
    return fake


def test_last_result_failed_shows_short_sanitized_error(monkeypatch):
    rows = [{
        "activity_id": 2,
        "created_at": "2026-10-07T12:00:00",
        "metadata": {"post_id": 7, "error": "400 for url https://graph.threads.net/x?access_token=ABC123SECRET"},
    }]
    recorder = []
    monkeypatch.setattr(database_module, "get_supabase", lambda: _fake_supabase(rows, recorder))

    result = posts_module._get_last_publish_result(USER, 7)

    assert result["status"] == "failed"
    assert result["at"] == "2026-10-07T12:00:00"
    assert "ABC123SECRET" not in result["error"]
    assert len(result["error"]) <= 200
    recorder[0].eq.assert_any_call("metadata->>post_id", "7")
    recorder[0].eq.assert_any_call("user_id", USER)


def test_last_result_published(monkeypatch):
    rows = [{"activity_id": 1, "created_at": "t", "metadata": {"post_id": 7}}]
    monkeypatch.setattr(database_module, "get_supabase", lambda: _fake_supabase(rows))
    assert posts_module._get_last_publish_result(USER, 7) == {"status": "published", "at": "t", "error": None}


def test_last_result_none_when_never_ran(monkeypatch):
    monkeypatch.setattr(database_module, "get_supabase", lambda: _fake_supabase([]))
    assert posts_module._get_last_publish_result(USER, 7) is None


def test_last_result_db_error_does_not_break(monkeypatch):
    fake = MagicMock()
    fake.table.side_effect = RuntimeError("db down")
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    assert posts_module._get_last_publish_result(USER, 7) is None


def test_get_post_includes_last_result(auth_client, monkeypatch):
    rows = [{"activity_id": 2, "created_at": "t", "metadata": {"post_id": 7, "error": "Credencial do Threads não conectada."}}]
    monkeypatch.setattr(database_module, "get_supabase", lambda: _fake_supabase(rows))
    res = auth_client.get("/posts/7")
    assert res.status_code == 200
    assert res.json()["last_result"]["status"] == "failed"
    assert "Threads" in res.json()["last_result"]["error"]


def test_publish_message_does_not_claim_success(auth_client, monkeypatch):
    fake = _fake_supabase([])

    def table(name):
        q = MagicMock()
        for m in ("select", "eq", "is_", "order", "limit", "in_", "maybe_single", "single"):
            getattr(q, m).return_value = q
        if name == "posts":
            q.execute.return_value = MagicMock(data={"id": 7, "user_id": USER})
        elif name == "schedulers":
            q.execute.return_value = MagicMock(data={"id": "job-1"})
        else:
            q.execute.return_value = MagicMock(data=[])
        return q

    fake.table.side_effect = table
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)

    async def fake_run(job_id):
        return None

    monkeypatch.setattr(posts_module, "run_scheduler_job", fake_run)
    actions = []
    monkeypatch.setattr(
        posts_module,
        "log_action",
        lambda *args, **kwargs: actions.append((args, kwargs)),
    )

    res = auth_client.post("/posts/7/publish")
    assert res.status_code == 200
    assert "disparada" not in res.json()["msg"]
    assert "resultado" in res.json()["msg"]
    assert actions == [
        (("post_publish_requested", "network=threads post_id=7 job_id=job-1"), {
            "user_id": USER,
            "profile_id": None,
        })
    ]

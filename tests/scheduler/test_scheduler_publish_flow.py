"""
Fluxo "Agora" e falhas de publicação no scheduler (tudo mockado).
"""

import sys
from datetime import datetime, time, timedelta
from types import SimpleNamespace

import pytz
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

import shopee_bot.scheduler as sched
import shopee_bot.scheduler.bot_post  # noqa: F401
from shopee_bot.database.activity_types import ActivityType

bot = sys.modules["shopee_bot.scheduler.bot_post"]


def test_job_defaults_tolerate_now_jobs():
    assert sched.JOB_DEFAULTS["misfire_grace_time"] >= 60
    assert sched.JOB_DEFAULTS["coalesce"] is True


def test_recurring_job_uses_all_selected_weekdays_without_changing_legacy_jobs(monkeypatch):
    calls = []

    class SchedulerRecorder:
        def add_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(sched, "_scheduler", SchedulerRecorder())
    monkeypatch.setattr(sched.schedulers, "insert", lambda *_args: 77)
    common = {
        "post_id": 7,
        "func": "bot_post",
        "trigger": "cron",
        "time": time(9, 0),
        "profile_id": "profile-a",
    }

    sched._add_job("user-1", {**common, "days_of_week": [0, 2, 4]}, object())
    sched._add_job("user-1", {**common, "day_of_week": 0}, object())

    assert calls[0]["day_of_week"] == "0,2,4"
    assert calls[1]["day_of_week"] == "0"


def _capture_activities(monkeypatch, module):
    calls = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, kind, activity, open_conn=None, profile_id=None:
            calls.append((user_id, kind, activity["metadata"], profile_id)),
    )
    return calls


def test_listener_records_uncaught_error_as_post_failure(monkeypatch):
    monkeypatch.setattr(
        sched.schedulers,
        "get_by_id",
        lambda job_id: {"user_id": "u1", "post_id": 7, "profile_id": "p1", "func": "bot_post"},
    )
    calls = _capture_activities(monkeypatch, sched)
    sched._on_job_problem(SimpleNamespace(job_id="5", code=EVENT_JOB_ERROR, exception=RuntimeError("Credencial do Threads não conectada.")))
    assert calls == [("u1", ActivityType.BOT_POST_FAILURE,
                      {
                          "network": "threads", "job_id": "5", "post_id": 7,
                          "stage": "scheduler",
                          "error": "RuntimeError: Credencial do Threads não conectada.",
                      }, "p1")]


def test_listener_records_missed_job(monkeypatch):
    monkeypatch.setattr(sched.schedulers, "get_by_id", lambda job_id: {"user_id": "u1", "post_id": 7})
    calls = _capture_activities(monkeypatch, sched)
    sched._on_job_problem(SimpleNamespace(job_id="5", code=EVENT_JOB_MISSED, exception=None))
    assert calls[0][2]["error"] == sched.MISSED_JOB_MESSAGE


def test_listener_ignores_jobs_without_post(monkeypatch):
    monkeypatch.setattr(sched.schedulers, "get_by_id", lambda job_id: {"user_id": "u1", "post_id": None})
    calls = _capture_activities(monkeypatch, sched)
    sched._on_job_problem(SimpleNamespace(job_id="5", code=EVENT_JOB_ERROR, exception=ValueError("x")))
    assert calls == []


def _noop(job_id):
    return None


def test_run_job_advances_pending_date_job_instead_of_duplicating(monkeypatch):
    tz = pytz.timezone("America/Sao_Paulo")
    scheduler = BackgroundScheduler(
        jobstores={"default": MemoryJobStore(), "on_demand": MemoryJobStore()}, timezone=tz,
    )
    scheduler.start(paused=True)
    try:
        scheduler.add_job(_noop, "date", id="9", args=("9",), run_date=datetime.now(tz) + timedelta(minutes=5))
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched.schedulers, "get_by_id", lambda job_id: {"func": "bot_post"})

        sched.run_job("9")

        job = scheduler.get_job("9", jobstore="default")
        assert job.next_run_time <= datetime.now(tz) + timedelta(seconds=2)
        assert scheduler.get_jobs(jobstore="on_demand") == []
    finally:
        scheduler.shutdown(wait=False)


def test_legacy_media_is_rejected_even_when_local_file_exists(monkeypatch, tmp_path):
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    monkeypatch.setattr(
        bot.schedulers, "get_by_id", lambda job_id: {"user_id": "u1", "post_id": 7, "profile_id": "p1"}
    )
    monkeypatch.setattr(bot.threads_credentials, "get_by_user_id",
                        lambda user_id, profile_id=None: {"username": "f", "threads_user_id": "1", "threads_access_token": "t"})
    monkeypatch.setattr(bot.posts, "get", lambda user_id, post_id, profile_id=None: [
        {"text": "oi", "medias": [{"type": "IMAGE", "file_path": str(img)}]},
    ])
    calls = _capture_activities(monkeypatch, bot)

    bot.bot_post("5")

    assert calls[0][1] == ActivityType.BOT_POST_FAILURE
    assert "Reenvie a mídia" in calls[0][2]["error"]


def test_media_post_with_missing_file_says_reupload(monkeypatch):
    monkeypatch.setattr(
        bot.schedulers, "get_by_id", lambda job_id: {"user_id": "u1", "post_id": 7, "profile_id": "p1"}
    )
    monkeypatch.setattr(bot.threads_credentials, "get_by_user_id",
                        lambda user_id, profile_id=None: {"username": "f", "threads_user_id": "1", "threads_access_token": "t"})
    monkeypatch.setattr(bot.posts, "get", lambda user_id, post_id, profile_id=None: [
        {"text": "oi", "medias": [{"type": "IMAGE", "file_path": "/nao/existe.jpg"}]},
    ])
    calls = _capture_activities(monkeypatch, bot)

    bot.bot_post("5")

    assert "Reenvie a mídia" in calls[0][2]["error"]


def test_bot_post_without_threads_credential_raises_clear_error(monkeypatch):
    monkeypatch.setattr(
        bot.schedulers, "get_by_id", lambda job_id: {"user_id": "u1", "post_id": 7, "profile_id": "p1"}
    )
    monkeypatch.setattr(bot.threads_credentials, "get_by_user_id", lambda user_id, profile_id=None: None)
    try:
        bot.bot_post("5")
    except RuntimeError as exc:
        assert "Credenciais" in str(exc)
    else:
        raise AssertionError("esperava RuntimeError")


def test_add_job_returns_persisted_id_and_releases_connection(monkeypatch):
    from contextlib import nullcontext
    from psycopg.pq import TransactionStatus

    class FakeConnection:
        info = SimpleNamespace(transaction_status=TransactionStatus.IDLE)

        def transaction(self):
            return nullcontext()

    conn = FakeConnection()
    released = []
    scheduled = []
    monkeypatch.setattr(sched, "get_conn", lambda: conn)
    monkeypatch.setattr(sched, "put_conn", lambda c: released.append(c))
    monkeypatch.setattr(sched.schedulers, "insert", lambda *_args: "8cbe9ecb-3dc7-4fe5-a864-573c385c73c4")
    monkeypatch.setattr(
        sched, "_scheduler",
        SimpleNamespace(add_job=lambda **kwargs: scheduled.append(kwargs)),
    )

    job_id = sched.add_job("user-1", {
        "post_id": 7, "func": "bot_post", "trigger": "cron",
        "time": time(13, 0), "days_of_week": [0, 2],
        "profile_id": "profile-a",
    })

    assert job_id == "8cbe9ecb-3dc7-4fe5-a864-573c385c73c4"
    assert len(scheduled) == 1
    assert scheduled[0]["id"] == job_id
    assert scheduled[0]["day_of_week"] == "0,2"
    assert released == [conn]


def test_add_job_releases_connection_when_scheduler_rejects_job(monkeypatch):
    from contextlib import nullcontext
    from psycopg.pq import TransactionStatus
    import pytest

    class FakeConnection:
        info = SimpleNamespace(transaction_status=TransactionStatus.IDLE)

        def transaction(self):
            return nullcontext()

    conn = FakeConnection()
    released = []
    monkeypatch.setattr(sched, "get_conn", lambda: conn)
    monkeypatch.setattr(sched, "put_conn", lambda c: released.append(c))
    monkeypatch.setattr(sched.schedulers, "insert", lambda *_args: "job-1")

    def reject(**_kwargs):
        raise RuntimeError("jobstore indisponível")

    monkeypatch.setattr(sched, "_scheduler", SimpleNamespace(add_job=reject))
    with pytest.raises(RuntimeError, match="jobstore"):
        sched.add_job("user-1", {
            "post_id": 7, "func": "bot_post", "trigger": "date",
            "run_date": datetime(2030, 1, 1), "profile_id": "profile-a",
        })
    assert released == [conn]

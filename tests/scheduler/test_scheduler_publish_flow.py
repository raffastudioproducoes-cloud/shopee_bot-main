"""
Fluxo "Agora" e falhas de publicação no scheduler (tudo mockado).
"""

import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytz
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

import shopee_bot.scheduler as sched
import shopee_bot.scheduler.bot_post  # noqa: F401
from shopee_bot.apis import cloudinary as cloud
from shopee_bot.database.activity_types import ActivityType

bot = sys.modules["shopee_bot.scheduler.bot_post"]


def test_job_defaults_tolerate_now_jobs():
    assert sched.JOB_DEFAULTS["misfire_grace_time"] >= 60
    assert sched.JOB_DEFAULTS["coalesce"] is True


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


def test_media_post_without_cloudinary_config_fails_with_clear_message(monkeypatch, tmp_path):
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    monkeypatch.setattr(cloud, "API_KEY", None)
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
    assert "não configurado" in calls[0][2]["error"]
    assert "Must supply" not in calls[0][2]["error"]


def test_media_post_with_missing_file_says_reupload(monkeypatch):
    monkeypatch.setattr(cloud, "NAME", "n")
    monkeypatch.setattr(cloud, "API_KEY", "k")
    monkeypatch.setattr(cloud, "SECRET", "s")
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

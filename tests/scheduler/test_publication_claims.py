import sys

import pytest

import shopee_bot.scheduler as scheduler


def _publication_job(func="bot_post"):
    return {
        "id": "job-1", "post_id": 7, "user_id": "user-1",
        "profile_id": "profile-1", "func": func, "trigger": "date",
    }


def _ready_publish_queue(monkeypatch):
    queue = sys.modules["shopee_bot.database.publish_jobs"]
    monkeypatch.setattr(queue, "enqueue", lambda **_kwargs: {"id": "queue-1", "status": "pending"})
    monkeypatch.setattr(queue, "claim", lambda *_args: {"id": "queue-1", "claim_token": "queue-claim"})
    return queue


def test_scheduler_enabled_defaults_to_true_and_can_disable(monkeypatch):
    monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)
    assert scheduler.scheduler_enabled() is True

    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    assert scheduler.scheduler_enabled() is False


def test_052_claim_migration_has_atomic_expiring_lease():
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "052_create_publication_claims.sql"
    ).read_text(encoding="utf-8").lower()

    assert "scheduler_id uuid primary key" in sql
    assert "references public.schedulers(id) on delete cascade" in sql

    claim_source = (
        Path(__file__).resolve().parents[2] / "database" / "publication_claims.py"
    ).read_text(encoding="utf-8").lower()
    assert "on conflict (scheduler_id) do update" in claim_source
    assert "make_interval(secs => %s)" in claim_source
    assert "where publication_claims.claimed_at <" in claim_source
    assert "where scheduler_id = %s and claim_token = %s" in claim_source


def test_try_claim_returns_token_only_when_database_claims(monkeypatch):
    from shopee_bot.database import publication_claims

    seen = {}

    def fake_query(sql, args, one=False):
        seen.update(sql=sql, args=args, one=one)
        return {"claim_token": "lease-1"}

    monkeypatch.setattr(publication_claims, "query_db", fake_query)

    assert publication_claims.try_claim("job-1", 300) == "lease-1"
    assert seen["args"] == ("job-1", 300)
    assert seen["one"] is True


def test_execute_publication_claims_runs_and_releases(monkeypatch):
    claims = sys.modules["shopee_bot.database.publication_claims"]
    calls = []

    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda job_id: _publication_job())
    monkeypatch.setattr(claims, "try_claim", lambda job_id, seconds: "lease-1")
    monkeypatch.setattr(claims, "release", lambda job_id, token: calls.append(("release", job_id, token)))
    monkeypatch.setattr(scheduler, "bot_post", lambda job_id: calls.append(("bot", job_id)))
    queue = _ready_publish_queue(monkeypatch)
    monkeypatch.setattr(queue, "finish", lambda *args, **kwargs: calls.append(("finish", args, kwargs)))

    scheduler.execute_publication("job-1")

    assert calls[0] == ("bot", "job-1")
    assert calls[-1] == ("release", "job-1", "lease-1")


def test_execute_publication_persists_confirmed_network_id(monkeypatch):
    claims = sys.modules["shopee_bot.database.publication_claims"]
    calls = []
    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda _job_id: _publication_job())
    monkeypatch.setattr(claims, "try_claim", lambda *_: "lease-1")
    monkeypatch.setattr(claims, "release", lambda *_: None)
    queue = _ready_publish_queue(monkeypatch)
    monkeypatch.setattr(queue, "finish", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(scheduler, "bot_post", lambda _job_id: scheduler.PublicationResult("succeeded", "network-7"))

    scheduler.execute_publication("job-1")

    assert calls == [(("queue-1", "queue-claim", "succeeded"), {"external_id": "network-7", "error": None})]


def test_execute_publication_skips_when_another_worker_owns_lease(monkeypatch):
    claims = sys.modules["shopee_bot.database.publication_claims"]
    calls = []

    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda job_id: _publication_job())
    monkeypatch.setattr(claims, "try_claim", lambda *_: None)
    monkeypatch.setattr(scheduler, "bot_post", lambda job_id: calls.append(job_id))
    monkeypatch.setattr(claims, "release", lambda *_: calls.append("released"))

    scheduler.execute_publication("job-1")

    assert calls == []


def test_execute_publication_releases_lease_when_bot_raises(monkeypatch):
    claims = sys.modules["shopee_bot.database.publication_claims"]
    released = []

    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda job_id: _publication_job())
    monkeypatch.setattr(claims, "try_claim", lambda *_: "lease-1")
    monkeypatch.setattr(claims, "release", lambda *args: released.append(args))
    queue = _ready_publish_queue(monkeypatch)
    finished = []
    monkeypatch.setattr(queue, "finish", lambda *args, **kwargs: finished.append((args, kwargs)))

    def fail(_job_id):
        raise RuntimeError("network down")

    monkeypatch.setattr(scheduler, "bot_post", fail)

    with pytest.raises(RuntimeError, match="network down"):
        scheduler.execute_publication("job-1")

    assert released == [("job-1", "lease-1")]
    assert finished[0][0][2] == "unknown"


def test_execute_publication_does_not_mask_bot_error_when_release_fails(monkeypatch):
    claims = sys.modules["shopee_bot.database.publication_claims"]

    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda job_id: _publication_job())
    monkeypatch.setattr(claims, "try_claim", lambda *_: "lease-1")
    monkeypatch.setattr(claims, "release", lambda *_: (_ for _ in ()).throw(RuntimeError("db down")))
    monkeypatch.setattr(scheduler, "bot_post", lambda _job_id: (_ for _ in ()).throw(RuntimeError("network down")))
    queue = _ready_publish_queue(monkeypatch)
    monkeypatch.setattr(queue, "finish", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimeError, match="network down"):
        scheduler.execute_publication("job-1")


def test_scheduled_and_on_demand_jobs_use_claiming_wrapper(monkeypatch):
    from datetime import datetime, time

    added = []

    class Recorder:
        def add_job(self, **kwargs):
            added.append(kwargs)

        def get_job(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(scheduler, "_scheduler", Recorder())
    monkeypatch.setattr(scheduler.schedulers, "insert", lambda *_: "job-1")
    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda *_: {"func": "bot_post"})

    scheduler._add_job("user-1", {
        "post_id": 7, "func": "bot_post", "trigger": "date",
        "run_date": datetime.now(), "profile_id": "profile-1",
    }, object())
    scheduler._add_job("user-1", {
        "post_id": 7, "func": "bot_post", "trigger": "cron",
        "time": time(9, 0), "day_of_week": 1, "profile_id": "profile-1",
    }, object())
    scheduler.run_job("job-1")

    assert [item["func"] for item in added] == [
        scheduler.execute_publication,
        scheduler.execute_publication,
        scheduler.execute_publication,
    ]


def test_existing_publication_jobs_are_upgraded_to_claiming_wrapper(monkeypatch):
    updated = []

    class Recorder:
        def modify_job(self, *args, **kwargs):
            updated.append((args, kwargs))

    monkeypatch.setattr(scheduler, "_scheduler", Recorder())
    monkeypatch.setattr(
        scheduler.schedulers,
        "get_publication_jobs",
        lambda: [{"id": "job-1"}, {"id": "job-2"}],
    )

    scheduler._upgrade_existing_publication_jobs()

    assert updated == [
        (("job-1",), {"jobstore": "default", "func": scheduler.execute_publication, "args": ("job-1",)}),
        (("job-2",), {"jobstore": "default", "func": scheduler.execute_publication, "args": ("job-2",)}),
    ]

"""Ambientes main/staging usam o mesmo banco sem compartilhar execução.

Sem acesso a APIs externas, Render ou dados reais de clientes.
"""
from types import SimpleNamespace

import pytest

import shopee_bot.scheduler as scheduler
from shopee_bot.database import publish_jobs, schedulers
from shopee_bot.database.scheduler_environment import current_environment


@pytest.mark.parametrize("branch, expected", [
    ("main", "production"),
    ("staging", "staging"),
])
def test_render_branch_is_authoritative(monkeypatch, branch, expected):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_GIT_BRANCH", branch)
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "production" if expected == "staging" else "staging")
    assert current_environment() == expected


def test_unrecognized_render_branch_fails_closed(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_GIT_BRANCH", "preview")
    with pytest.raises(RuntimeError, match="somente main e staging"):
        current_environment()


def test_local_scheduler_env_is_explicit(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    assert current_environment() == "staging"
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "typo")
    with pytest.raises(RuntimeError):
        current_environment()


def test_scheduler_queries_are_partitioned(monkeypatch):
    seen = []
    monkeypatch.setattr(schedulers, "current_environment", lambda: "staging")
    monkeypatch.setattr(
        schedulers, "query_db",
        lambda sql, args, one=False: seen.append((sql, args)) or ([] if not one else None),
    )
    schedulers.get_publication_jobs()
    schedulers.get_by_id("job-1")
    assert "s.environment = %s" in seen[0][0]
    assert seen[0][1][-1] == "staging"
    assert "s.environment = %s" in seen[1][0]
    assert seen[1][1] == ("job-1", "staging")


def test_scheduler_insert_stamps_runtime_environment(monkeypatch):
    seen = {}
    monkeypatch.setattr(schedulers, "current_environment", lambda: "staging")
    monkeypatch.setattr(
        schedulers, "execute_db",
        lambda sql, args, _conn=None: seen.update(sql=sql, args=args) or "job-1",
    )
    schedulers.insert("user-1", {
        "post_id": 17, "func": "bot_post", "trigger": "cron",
        "profile_id": "profile-1",
    })
    assert "environment" in seen["sql"]
    assert seen["args"][-2:] == ("profile-1", "staging")


def test_recovery_filters_other_environment_before_claim(monkeypatch):
    calls = []
    monkeypatch.setattr(publish_jobs, "current_environment", lambda: "staging")
    monkeypatch.setattr(
        publish_jobs, "query_db",
        lambda sql, args, one=False: calls.append((sql, args)) or ([] if not one else None),
    )
    publish_jobs.recoverable(600)
    publish_jobs.expire_running(600)
    publish_jobs.claim("pending-1", "worker-1", 600)

    assert "schedule.environment = %s" in calls[0][0]
    assert calls[0][1] == (publish_jobs.RECOVERY_MAX_AGE_SECONDS, "staging", 100)
    assert "schedule.environment = %s" in calls[1][0]
    assert calls[1][1][-1] == "staging"
    assert "schedule.environment = %s" in calls[2][0]
    assert calls[2][1] == ("pending-1", "staging", "worker-1")
    assert "schedule.user_id = job.user_id" in calls[0][0]
    assert "schedule.profile_id IS NOT DISTINCT FROM job.profile_id" in calls[0][0]


def test_each_environment_has_its_own_apscheduler_table(monkeypatch):
    instances = []

    class FakeStore:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeScheduler:
        def __init__(self, **kwargs):
            instances.append(kwargs)

        def add_listener(self, *_args):
            pass

        def start(self, **_kwargs):
            pass

        def add_job(self, *_args, **_kwargs):
            pass

        def resume(self):
            pass

    monkeypatch.setattr(scheduler, "SQLAlchemyJobStore", FakeStore)
    monkeypatch.setattr(scheduler, "MemoryJobStore", lambda: object())
    monkeypatch.setattr(scheduler, "GeventScheduler", FakeScheduler)
    monkeypatch.setattr(scheduler, "_upgrade_existing_publication_jobs", lambda: None)
    monkeypatch.setattr(scheduler, "_jobstore_dsn", lambda: "postgresql+psycopg://db/test")

    for name in ("production", "staging"):
        monkeypatch.setattr(scheduler, "current_environment", lambda value=name: value)
        scheduler.init()

    assert [instance["jobstores"]["default"].kwargs["tablename"] for instance in instances] == [
        "apscheduler_jobs", "apscheduler_jobs_staging",
    ]


def test_foreign_environment_schedule_cannot_dispatch(monkeypatch):
    called = []
    monkeypatch.setattr(scheduler, "_shutting_down", False)
    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda _job: None)
    monkeypatch.setattr(
        scheduler.publication_claims, "try_claim",
        lambda *_args: called.append("claim"),
    )
    scheduler.execute_publication("another-environment-job")
    assert called == []


def test_migration_preserves_production_jobs():
    from pathlib import Path
    sql = (
        Path(__file__).resolve().parents[2] / "database" / "migrations"
        / "067_isolate_scheduler_environments.sql"
    ).read_text(encoding="utf-8").lower()
    assert "add column if not exists environment" in sql
    assert "default 'production'" in sql
    assert "create table if not exists public.apscheduler_jobs_staging" in sql
    assert "enable row level security" in sql
    assert "drop table" not in sql
    assert "truncate" not in sql

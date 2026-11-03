"""F0 Task 2: consultas/claims respeitam o gate, sem acessar banco real."""

import pytest

from shopee_bot.database import publish_jobs, schedulers


@pytest.fixture(autouse=True)
def configured_environment(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "production")


def test_production_reads_central_from_staging_but_does_not_import_legacy(monkeypatch):
    observed = {}

    def query(sql, args, one=False):
        observed.update(sql=sql, args=args, one=one)
        return None

    monkeypatch.setattr(schedulers, "query_db", query)
    assert schedulers.get_by_id("schedule-a") is None
    assert "s.dispatch_mode = 'central'" in observed["sql"]
    assert "s.dispatch_cancelled_at IS NULL" in observed["sql"]
    assert "s.environment = %s AND s.dispatch_mode = 'legacy'" in observed["sql"]
    assert observed["args"] == ("schedule-a", "production")
    assert observed["one"] is True


def test_staging_executes_only_its_legacy_when_gate_is_on(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    captured = {}

    def query(sql, args, one=False):
        captured.update(sql=sql, args=args)
        return None

    monkeypatch.setattr(schedulers, "query_db", query)
    schedulers.get_by_id("schedule-b")
    assert "s.environment = %s AND s.dispatch_mode = 'legacy'" in captured["sql"]
    assert "OR (s.dispatch_mode = 'central'" not in captured["sql"]
    assert captured["args"] == ("schedule-b", "staging")


def test_existing_jobstore_upgrade_does_not_claim_central_mirrors(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        schedulers,
        "query_db",
        lambda sql, args, one=False: captured.update(sql=sql, args=args) or [],
    )
    assert schedulers.get_publication_jobs() == []
    assert "s.dispatch_mode = 'legacy'" in captured["sql"]
    assert "s.dispatch_mode = 'central'" not in captured["sql"]


def test_recovery_and_claim_central_in_production_only(monkeypatch):
    calls = []

    def query(sql, args, one=False):
        calls.append((sql, args, one))
        return None if one else []

    monkeypatch.setattr(publish_jobs, "query_db", query)
    assert publish_jobs.recoverable(600) == []
    assert publish_jobs.claim("queue-a", "worker", 600) is None
    assert publish_jobs.expire_running(600) == []

    for sql, args, _ in calls:
        assert "schedule.dispatch_mode = 'central'" in sql
        assert "schedule.dispatch_cancelled_at IS NULL" in sql
        assert "schedule.environment = %s AND schedule.dispatch_mode = 'legacy'" in sql
        assert "production" in args

    calls.clear()
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    publish_jobs.recoverable(600)
    publish_jobs.claim("queue-b", "worker", 600)
    publish_jobs.expire_running(600)
    for sql, args, _ in calls:
        assert "schedule.dispatch_mode = 'legacy'" in sql
        assert "schedule.dispatch_mode = 'central'" not in sql
        assert "staging" in args


def test_disabled_flag_preserves_original_query_shape(monkeypatch):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "false")
    captured = {}
    monkeypatch.setattr(
        publish_jobs,
        "query_db",
        lambda sql, args, one=False: captured.update(sql=sql, args=args) or [],
    )
    assert publish_jobs.recoverable(600) == []
    assert "schedule.environment = %s" in captured["sql"]
    assert "schedule.dispatch_mode = 'legacy'" in captured["sql"]
    assert captured["args"] == (publish_jobs.RECOVERY_MAX_AGE_SECONDS, "production", 100)

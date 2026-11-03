"""Regressoes dos filtros positivos de origem na fila compartilhada."""
from shopee_bot.database import publish_jobs, schedulers


def test_legacy_readers_restrict_publication_origin(monkeypatch):
    captured = []
    monkeypatch.setattr(schedulers, "query_db", lambda sql, args, *a, **kw: captured.append(sql) or [])
    schedulers.get_publication_jobs()
    schedulers.get_by_id("schedule")
    schedulers.list_central_dispatch_jobs()
    assert all("publication_origin = 'legacy'" in query for query in captured)


def test_claim_and_recovery_are_legacy_only(monkeypatch):
    captured = []
    monkeypatch.setattr(publish_jobs, "query_db", lambda sql, args, **kw: captured.append(sql) or [])
    publish_jobs.claim("job", "worker", 600)
    publish_jobs.recoverable(600)
    publish_jobs.expire_running(600)
    publish_jobs.expire_stale_pending()
    assert len(captured) == 4
    assert all("publication_origin = 'legacy'" in query for query in captured)


def test_external_boundary_and_manual_requeue_are_legacy_only(monkeypatch):
    captured = []
    monkeypatch.setattr(publish_jobs, "query_db", lambda sql, args, **kw: captured.append(sql) or [])
    publish_jobs.mark_external_started("job", "claim")
    publish_jobs.requeue_if_safe("job", "claim")
    assert len(captured) == 2
    assert all("publication_origin = 'legacy'" in query for query in captured)

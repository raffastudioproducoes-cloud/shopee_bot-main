"""Guarda positiva na main, independente do dispatch central de staging."""
from shopee_bot.database import publish_jobs, schedulers


def test_main_scheduler_never_reads_campaign_rows(monkeypatch):
    queries = []
    monkeypatch.setattr(schedulers, "query_db", lambda sql, args, *a, **kw: queries.append(sql) or [])
    schedulers.get_publication_jobs()
    schedulers.get_by_id("schedule")
    assert len(queries) == 2
    assert all("publication_origin = 'legacy'" in item for item in queries)


def test_main_queue_claim_and_recovery_never_read_campaign(monkeypatch):
    queries = []
    monkeypatch.setattr(publish_jobs, "query_db", lambda sql, args, **kw: queries.append(sql) or [])
    publish_jobs.recoverable(600)
    publish_jobs.expire_running(600)
    publish_jobs.claim("job", "worker", 600)
    publish_jobs.mark_external_started("job", "claim")
    publish_jobs.requeue_if_safe("job", "claim")
    assert len(queries) == 5
    assert all("publication_origin = 'legacy'" in item for item in queries)

"""Regressão do incidente de 30/31-10: SIGTERM durante posts agendados.

Todos os casos usam mocks; nenhuma credencial, rede social ou linha real
do Supabase é acessada.
"""
from pathlib import Path
import signal

import pytest

import shopee_bot.scheduler as scheduler
from shopee_bot.database import publish_jobs
from shopee_bot.scheduler import publication_context


ROOT = Path(__file__).resolve().parents[2]


def test_migration_marks_old_running_as_uncertain():
    sql = (ROOT / "database/migrations/060_track_external_publish_start.sql").read_text()
    assert "ADD COLUMN IF NOT EXISTS external_started_at" in sql
    compatibility = (ROOT / "database/migrations/061_guard_legacy_publish_leases.sql").read_text()
    assert "ADD COLUMN IF NOT EXISTS preflight_claim_token UUID" in compatibility
    assert "WHERE status = 'running' AND external_started_at IS NULL" in sql


def test_expired_job_is_retried_only_before_external_call(monkeypatch):
    seen = {}

    def query(sql, params):
        seen["sql"] = sql.lower()
        seen["params"] = params
        return [
            {"id": "before-api", "status": "pending"},
            {"id": "after-api", "status": "unknown"},
        ]

    monkeypatch.setattr(publish_jobs, "query_db", query)
    result = publish_jobs.expire_running(600)
    assert [row["status"] for row in result] == ["pending", "unknown"]
    assert "preflight_claim_token is distinct from claim_token" in seen["sql"]
    assert "else 'pending'" in seen["sql"]
    assert "attempt >= %s then 'failed'" in seen["sql"]
    assert seen["params"][-1] == 600


def test_expired_preflight_is_bounded_to_five_attempts():
    assert publish_jobs.MAX_PREFLIGHT_ATTEMPTS == 5


def test_only_claim_owner_can_cross_external_boundary(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        publish_jobs, "query_db",
        lambda sql, args, one=False: seen.update(sql=sql, args=args) or {"id": "q1"},
    )
    assert publish_jobs.mark_external_started("q1", "claim-a")
    assert seen["args"] == ("q1", "claim-a", "claim-a")
    assert "preflight_claim_token = %s" in seen["sql"]
    assert "status = 'running'" in seen["sql"]


def test_preflight_requeue_is_conditional_on_no_external_call(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        publish_jobs, "query_db",
        lambda sql, args, one=False: seen.update(sql=sql, args=args) or {"id": "q1"},
    )
    publish_jobs.requeue_if_safe("q1", "claim-a")
    assert seen["args"] == ("q1", "claim-a", "claim-a")
    assert "external_started_at IS NULL" in seen["sql"]
    assert "claim_token = %s" in seen["sql"]


def test_worker_shutdown_defers_before_external_post(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "_shutting_down", False)
    monkeypatch.setattr(
        publish_jobs, "claim",
        lambda *_: {"id": "q1", "claim_token": "lease-a"},
    )
    monkeypatch.setattr(
        publish_jobs, "mark_external_started",
        lambda *_: calls.append("api-boundary") or {"id": "q1"},
    )
    monkeypatch.setattr(
        publish_jobs, "requeue_if_safe",
        lambda *_: calls.append("safe-requeue") or {"id": "q1"},
    )
    monkeypatch.setattr(
        publish_jobs, "finish",
        lambda *_args, **_kwargs: calls.append("finish"),
    )

    def fake_network(_job_id):
        scheduler.mark_shutting_down()  # SIGTERM no instante da preparação
        publication_context.mark_external_delivery()
        calls.append("POST REAL PROIBIDO")

    monkeypatch.setattr(scheduler, "bot_post", fake_network)
    try:
        scheduler._execute_publish_item("q1", {"id": "schedule-a", "func": "bot_post"})
    finally:
        scheduler._shutting_down = False

    assert calls == ["safe-requeue"]


def test_boundary_prevents_lost_lease_from_publishing(monkeypatch):
    monkeypatch.setattr(scheduler, "_shutting_down", False)
    monkeypatch.setattr(publish_jobs, "mark_external_started", lambda *_: None)
    token = publication_context.activate("q1", "lost")
    try:
        with pytest.raises(publication_context.PublicationDeferred):
            publication_context.mark_external_delivery()
    finally:
        publication_context.reset(token)


def test_standalone_publisher_without_queue_does_not_touch_database(monkeypatch):
    monkeypatch.setattr(
        publish_jobs, "mark_external_started",
        lambda *_: (_ for _ in ()).throw(AssertionError("database")),
    )
    publication_context.mark_external_delivery()


def test_successful_provider_call_records_boundary_once(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "_shutting_down", False)
    monkeypatch.setattr(
        publish_jobs, "mark_external_started",
        lambda *args: calls.append(args) or {"id": "q1"},
    )
    token = publication_context.activate("q1", "claim-a")
    try:
        publication_context.mark_external_delivery()
        assert calls == [("q1", "claim-a")]
    finally:
        publication_context.reset(token)


def test_worker_sigterm_stops_new_dispatch_and_run_drains(monkeypatch):
    from gunicorn.workers.ggevent import GeventWorker
    from shopee_bot.scheduler.gunicorn_worker import PublishingGeventWorker

    calls = []
    monkeypatch.setattr(scheduler, "_shutting_down", False)
    monkeypatch.setattr(
        GeventWorker, "handle_exit",
        lambda self, sig, frame: calls.append(("term", sig)),
    )
    monkeypatch.setattr(
        GeventWorker, "run",
        lambda self: calls.append("server-stopped"),
    )
    monkeypatch.setattr(
        scheduler, "shutdown_gracefully",
        lambda: calls.append("waited-publications"),
    )

    worker = object.__new__(PublishingGeventWorker)
    try:
        worker.handle_exit(signal.SIGTERM, None)
        assert scheduler.is_shutting_down()
        worker.run()
    finally:
        scheduler._shutting_down = False

    assert calls == [
        ("term", signal.SIGTERM),
        "server-stopped",
        "waited-publications",
    ]


def test_provider_publishers_mark_boundary_before_network_calls():
    publishers = [
        "bot_post.py", "bot_post_facebook.py", "bot_post_instagram.py",
        "bot_post_tiktok.py", "bot_post_x.py",
    ]
    for filename in publishers:
        source = (ROOT / "scheduler" / filename).read_text(encoding="utf-8")
        assert "mark_external_delivery()" in source
        assert "from shopee_bot.scheduler.publication_context import mark_external_delivery" in source


def test_legacy_worker_cannot_be_misclassified_as_recoverable(monkeypatch):
    """Claims criados pela main antiga não terão token de versão rastreada."""
    seen = {}
    monkeypatch.setattr(
        publish_jobs, "query_db",
        lambda sql, args: seen.update(sql=sql.lower(), args=args) or [],
    )
    publish_jobs.expire_running(600)
    assert "preflight_claim_token is distinct from claim_token" in seen["sql"]
    assert "when preflight_claim_token is distinct from claim_token" in seen["sql"]
    assert "unknown" in seen["sql"]


def test_new_worker_claim_binds_tracking_token_to_current_claim(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        publish_jobs, "query_db",
        lambda sql, args, one=False: seen.update(sql=sql.lower()) or {
            "id": "q1", "claim_token": "token-new"
        },
    )
    publish_jobs.claim("q1", "worker-new", 600)
    assert "preflight_claim_token = candidate.token" in seen["sql"]
    assert "claim_token = candidate.token" in seen["sql"]
    assert "external_started_at = null" in seen["sql"]

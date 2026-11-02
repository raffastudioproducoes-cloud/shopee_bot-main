"""Evidência reproduzível da lacuna F0 entre staging e executor central.

Testes de contrato com banco/scheduler simulados. Nenhum dado real, Render,
Supabase, HTTP de provedor ou execução de postagem é acessado.
A expectativa futura fica em xfail até o reconciliador da Task 2 existir.
"""

from datetime import datetime, timezone

import pytest

import shopee_bot.scheduler as scheduler
from shopee_bot.database import publish_jobs, schedulers


STAGING_SCHEDULE = {
    "id": "agenda-staging-1",
    "post_id": 42,
    "user_id": "usuario-desenvolvedor",
    "profile_id": "perfil-teste",
    "func": "bot_post",
    "trigger": "date",
    "environment": "staging",
}


def _schedule_lookup_for_staging_row(sql, args, one=False):
    """Simula uma única linha com environment=staging no Supabase comum."""
    assert one is True
    assert "s.environment = %s" in sql
    assert args[0] == STAGING_SCHEDULE["id"]
    return STAGING_SCHEDULE.copy() if args[1] == "staging" else None


def test_f0_current_schedule_lookup_is_runtime_partitioned(monkeypatch):
    """Estado atual: a produção não lê uma linha de agenda de staging."""
    monkeypatch.setattr(schedulers, "query_db", _schedule_lookup_for_staging_row)

    monkeypatch.setattr(schedulers, "current_environment", lambda: "staging")
    assert schedulers.get_by_id(STAGING_SCHEDULE["id"]) == STAGING_SCHEDULE

    monkeypatch.setattr(schedulers, "current_environment", lambda: "production")
    assert schedulers.get_by_id(STAGING_SCHEDULE["id"]) is None


def test_f0_current_recovery_and_claim_skip_staging_rows_in_production(monkeypatch):
    """A fila atual também filtra o ambiente da agenda no mesmo SQL."""
    captured = []

    def fake_queue_query(sql, args, one=False):
        captured.append((sql, args, one))
        assert "schedule.environment = %s" in sql
        if "FROM publish_jobs job" in sql and "ORDER BY job.created_at" in sql:
            return [{"id": "fila-staging-1", "scheduler_id": STAGING_SCHEDULE["id"]}] if args[0] == "staging" else []
        if "FOR UPDATE OF job SKIP LOCKED" in sql:
            return {"id": "fila-staging-1", "claim_token": "lease-simulado"} if args[1] == "staging" else None
        raise AssertionError("Query inesperada neste teste de regressão")

    monkeypatch.setattr(publish_jobs, "query_db", fake_queue_query)

    monkeypatch.setattr(publish_jobs, "current_environment", lambda: "staging")
    assert len(publish_jobs.recoverable(600)) == 1
    assert publish_jobs.claim("fila-staging-1", "worker-staging", 600) is not None

    monkeypatch.setattr(publish_jobs, "current_environment", lambda: "production")
    assert publish_jobs.recoverable(600) == []
    assert publish_jobs.claim("fila-staging-1", "worker-production", 600) is None
    assert len(captured) == 4


def test_f0_current_creation_uses_local_apscheduler(monkeypatch):
    """Uma criação hoje registra o trigger somente no jobstore do processo."""
    calls = []

    class LocalScheduler:
        def add_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(scheduler, "_scheduler", LocalScheduler())
    monkeypatch.setattr(scheduler.schedulers, "insert", lambda *_args: STAGING_SCHEDULE["id"])

    created = scheduler._add_job(
        STAGING_SCHEDULE["user_id"],
        {
            "post_id": STAGING_SCHEDULE["post_id"],
            "profile_id": STAGING_SCHEDULE["profile_id"],
            "func": STAGING_SCHEDULE["func"],
            "trigger": "date",
            "run_date": datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc),
        },
        None,
    )
    assert created == STAGING_SCHEDULE["id"]
    assert len(calls) == 1
    assert calls[0]["id"] == STAGING_SCHEDULE["id"]
    assert calls[0]["trigger"] == "date"
    assert calls[0]["func"] is scheduler.execute_publication


@pytest.mark.xfail(
    strict=True,
    reason="F0 Task 2 pendente: não há reconciliação durável staging → executor de produção",
)
def test_f0_future_contract_production_can_dispatch_staging_intent(monkeypatch):
    """Contrato desejado: agenda criada em staging chega ao executor central."""
    monkeypatch.setattr(schedulers, "query_db", _schedule_lookup_for_staging_row)
    monkeypatch.setattr(schedulers, "current_environment", lambda: "production")
    assert schedulers.get_by_id(STAGING_SCHEDULE["id"]) == STAGING_SCHEDULE

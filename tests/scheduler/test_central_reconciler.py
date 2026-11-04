"""F0: reconciliador central e isolamento do jobstore (somente mocks)."""

from datetime import datetime, time
from types import SimpleNamespace

import pytest

import shopee_bot.scheduler as scheduler
from shopee_bot.scheduler import central_reconciler
from shopee_bot.database import schedulers


class FakeScheduler:
    def __init__(self):
        self.jobs = {"legacy-id": SimpleNamespace(id="legacy-id", name="original")}
        self.created = []
        self.removed = []

    def get_job(self, identifier, jobstore=None):
        assert jobstore == "default"
        return self.jobs.get(identifier)

    def get_jobs(self, jobstore=None):
        assert jobstore == "default"
        return list(self.jobs.values())

    def add_job(self, **kwargs):
        self.created.append(kwargs)
        self.jobs[kwargs["id"]] = SimpleNamespace(
            id=kwargs["id"], name=kwargs["name"],
        )

    def remove_job(self, identifier):
        self.removed.append(identifier)
        del self.jobs[identifier]


def row(id="c-1", revision=1, trigger="cron"):
    return {
        "id": id, "dispatch_revision": revision, "trigger": trigger,
        "time": time(14, 30), "days_of_week": [0, 2, 4],
        "day_of_week": 0, "start_date": None,
        "run_date": datetime(2026, 11, 5, 12, 0),
    }


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "production")
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "true")


def test_central_mirror_is_prefixed_and_idempotent(monkeypatch):
    monkeypatch.setattr(schedulers, "list_central_dispatch_jobs", lambda: [row()])
    jobs = FakeScheduler()
    publisher = lambda _id: None

    central_reconciler.reconcile(jobs, publisher)
    assert len(jobs.created) == 1
    created = jobs.created[0]
    assert created["id"] == "central:c-1"
    assert created["args"] == ("c-1",)
    assert created["day_of_week"] == "0,2,4"
    assert created["jobstore"] == "default"
    assert created["func"] is publisher
    assert "legacy-id" in jobs.jobs

    central_reconciler.reconcile(jobs, publisher)
    assert len(jobs.created) == 1
    assert jobs.removed == []


def test_central_revision_and_cancellation_preserve_legacy(monkeypatch):
    state = [row()]
    monkeypatch.setattr(schedulers, "list_central_dispatch_jobs", lambda: state)
    jobs = FakeScheduler()
    central_reconciler.reconcile(jobs, lambda *_: None)

    state = [row(revision=2, trigger="date")]
    central_reconciler.reconcile(jobs, lambda *_: None)
    assert len(jobs.created) == 2
    assert jobs.created[1]["trigger"] == "date"
    assert jobs.created[1]["run_date"] == datetime(2026, 11, 5, 12, 0)

    state = []
    central_reconciler.reconcile(jobs, lambda *_: None)
    assert jobs.removed == ["central:c-1"]
    assert "legacy-id" in jobs.jobs


def test_stage_creates_durable_intent_without_local_aps_entry(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    monkeypatch.setattr(scheduler.schedulers, "insert", lambda *_args: "central-a")
    class NoLocal:
        def add_job(self, **_kwargs):
            pytest.fail("Staging não pode criar job local quando central está habilitado")
    monkeypatch.setattr(scheduler, "_scheduler", NoLocal())
    result = scheduler._add_job(
        "owner", {
            "post_id": 17, "profile_id": "profile",
            "func": "bot_post", "trigger": "date",
            "run_date": datetime(2026, 11, 5, 12, 0),
        }, None,
    )
    assert result == "central-a"


def test_central_mirror_never_dispatches_when_gate_is_off(monkeypatch):
    seen = []
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "false")
    monkeypatch.setattr(scheduler, "_shutting_down", False)
    monkeypatch.setattr(scheduler, "execute_publication", lambda x: seen.append(x))
    scheduler.execute_central_publication("central-a")
    assert seen == []


def test_central_mirror_dispatches_only_authorized_active_row(monkeypatch):
    seen = []
    monkeypatch.setattr(scheduler, "_shutting_down", False)
    monkeypatch.setattr(
        scheduler.schedulers,
        "get_by_id",
        lambda _id: {"dispatch_mode": "central"},
    )
    monkeypatch.setattr(scheduler, "execute_publication", lambda x: seen.append(x))
    scheduler.execute_central_publication("central-a")
    assert seen == ["central-a"]

    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    scheduler.execute_central_publication("central-a")
    assert seen == ["central-a"]


def test_production_lists_only_active_central_without_date_replay(monkeypatch):
    collected = {}
    monkeypatch.setattr(
        schedulers, "query_db",
        lambda sql, args: collected.update(sql=sql, args=args) or [],
    )
    assert schedulers.list_central_dispatch_jobs() == []
    assert "dispatch_mode = 'central'" in collected["sql"]
    assert "dispatch_cancelled_at IS NULL" in collected["sql"]
    assert "NOT EXISTS" in collected["sql"]
    assert "publish_jobs" in collected["sql"]

    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    def blocked(*_args, **_kwargs):
        pytest.fail("Staging não deve consultar a fila central da produção")
    monkeypatch.setattr(schedulers, "query_db", blocked)
    assert schedulers.list_central_dispatch_jobs() == []


def test_central_cancel_is_soft_and_scope_checked(monkeypatch):
    state = {}
    monkeypatch.setattr(
        schedulers, "execute_db",
        lambda sql, args, conn=None: state.update(sql=sql, args=args) or "central-a",
    )
    assert schedulers.cancel_central("owner", "central-a") == "central-a"
    assert "UPDATE schedulers" in state["sql"]
    assert "dispatch_cancelled_at = now()" in state["sql"]
    assert "dispatch_revision = dispatch_revision + 1" in state["sql"]
    assert "DELETE FROM" not in state["sql"]
    assert state["args"] == ("central-a", "owner", "production")


def test_central_run_now_persists_brasilia_time_without_creating_duplicate(monkeypatch):
    state = {}
    monkeypatch.setattr(
        schedulers, "execute_db",
        lambda sql, args: state.update(sql=sql, args=args) or "central-a",
    )
    assert schedulers.expedite_central("central-a") == "central-a"
    assert "AT TIME ZONE 'America/Sao_Paulo'" in state["sql"]
    assert "pj.scheduler_id = s.id" in state["sql"]
    assert "s.trigger = 'date'" in state["sql"]
    assert state["args"] == ("central-a", "production")


def test_remove_central_never_deletes_history_or_local_jobs(monkeypatch):
    called = []
    monkeypatch.setattr(scheduler.schedulers, "cancel_central", lambda *_args: "central-a")
    monkeypatch.setattr(scheduler.schedulers, "delete", lambda *_args: called.append("delete"))
    monkeypatch.setattr(scheduler, "_scheduler", SimpleNamespace(
        get_job=lambda *_args: called.append("get_job"),
        remove_job=lambda *_args: called.append("remove_job"),
    ))
    scheduler._remove_job("owner", "central-a", None)
    assert called == []


def test_run_now_in_staging_sets_intent_for_production_only(monkeypatch):
    called = []
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    monkeypatch.setattr(scheduler.schedulers, "expedite_central", lambda _id: "central-a")
    monkeypatch.setattr(scheduler, "reconcile_central_jobs", lambda: called.append("reconcile"))
    monkeypatch.setattr(scheduler, "_scheduler", SimpleNamespace(
        get_job=lambda *_args, **_kw: pytest.fail("Staging não pode executar o mirror"),
    ))
    scheduler.run_job("central-a")
    assert called == ["reconcile"]


def test_new_central_insert_records_dispatch_mode_and_original_owner(monkeypatch):
    seen = {}
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    monkeypatch.setattr(
        schedulers, "execute_db",
        lambda sql, args, conn=None: seen.update(sql=sql, args=args) or "central-a",
    )
    result = schedulers.insert(
        "owner", {
            "post_id": 17, "profile_id": "profile",
            "func": "bot_post", "trigger": "date",
            "run_date": datetime(2026, 11, 5, 12, 0),
        },
    )
    assert result == "central-a"
    assert "dispatch_mode" in seen["sql"]
    assert seen["args"][-3:] == ("profile", "staging", "central")



def test_expired_date_produces_terminal_failed_without_external_retry(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        schedulers, "query_db",
        lambda sql, args: captured.update(sql=sql, args=args) or [],
    )
    assert schedulers.expire_missed_central_dates(3600) == []
    sql = captured["sql"]
    assert "INSERT INTO publish_jobs" in sql
    assert "s.id::text, 'failed'" in sql
    assert "ON CONFLICT (idempotency_key) DO NOTHING" in sql
    assert "NOT EXISTS" in sql
    assert "dispatch_mode = 'central'" in sql
    assert captured["args"][1] == 3600


def test_staging_never_expires_central_dates(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    monkeypatch.setattr(
        schedulers, "query_db",
        lambda *_a, **_kw: pytest.fail("Somente produção pode marcar expiração"),
    )
    assert schedulers.expire_missed_central_dates() == []


def test_run_now_repeated_calls_return_same_id_without_replay(monkeypatch):
    captured = []
    monkeypatch.setattr(
        schedulers, "execute_db",
        lambda sql, args: captured.append((sql, args)) or "central-a",
    )
    assert schedulers.expedite_central("central-a") == "central-a"
    assert schedulers.expedite_central("central-a") == "central-a"
    assert len(captured) == 2
    for sql, args in captured:
        assert "NOT EXISTS" in sql
        assert "THEN 1 ELSE 0" in sql
        assert args == ("central-a", "production")

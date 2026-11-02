"""F0: contrato do gate de transição, sem banco nem publicação externa."""

from pathlib import Path

import pytest

from shopee_bot.database.central_dispatch import (
    can_execute_schedule,
    central_dispatch_enabled,
    new_schedule_dispatch_mode,
    publication_scope_sql,
)


@pytest.fixture(autouse=True)
def neutral_render(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_GIT_BRANCH", raising=False)
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "production")
    monkeypatch.delenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", raising=False)


def test_gate_fails_closed_and_all_old_agendas_remain_legacy():
    assert central_dispatch_enabled() is False
    assert new_schedule_dispatch_mode() == "legacy"
    assert can_execute_schedule(source_environment="staging", dispatch_mode="central") is False
    sql, params = publication_scope_sql()
    assert sql == "schedule.environment = %s AND schedule.dispatch_mode = 'legacy'"
    assert params == ("production",)


@pytest.mark.parametrize("bad", ["maybe", "enabled", "production", "tru"])
def test_invalid_gate_is_rejected(monkeypatch, bad):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", bad)
    with pytest.raises(ValueError, match="ORBITAL_CENTRAL_DISPATCH_ENABLED"):
        central_dispatch_enabled()


def test_legacy_staging_continues_locally_and_never_moves_to_production(monkeypatch):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "staging")
    assert can_execute_schedule(source_environment="staging", dispatch_mode="legacy")
    assert not can_execute_schedule(source_environment="production", dispatch_mode="legacy")
    assert not can_execute_schedule(source_environment="staging", dispatch_mode="central")
    sql, args = publication_scope_sql()
    assert "dispatch_mode = 'legacy'" in sql
    assert args == ("staging",)

    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "production")
    assert not can_execute_schedule(source_environment="staging", dispatch_mode="legacy")


def test_production_can_claim_only_opted_in_central_and_local_legacy(monkeypatch):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "true")
    assert new_schedule_dispatch_mode() == "central"
    assert can_execute_schedule(source_environment="staging", dispatch_mode="central")
    assert can_execute_schedule(source_environment="production", dispatch_mode="central")
    assert can_execute_schedule(source_environment="production", dispatch_mode="legacy")
    assert not can_execute_schedule(source_environment="staging", dispatch_mode="legacy")
    sql, params = publication_scope_sql()
    assert "environment = %s AND schedule.dispatch_mode = 'legacy'" in sql
    assert "schedule.dispatch_mode = 'central'" in sql
    assert "dispatch_cancelled_at IS NULL" in sql
    assert params == ("production",)


def test_cancelled_central_never_dispatches(monkeypatch):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "true")
    assert not can_execute_schedule(
        source_environment="staging", dispatch_mode="central", cancelled=True,
    )
    assert not can_execute_schedule(
        source_environment="production", dispatch_mode="legacy", cancelled=True,
    )


def test_unknown_mode_and_unsafe_sql_alias_fail_closed():
    assert not can_execute_schedule(source_environment="production", dispatch_mode="unknown")
    with pytest.raises(ValueError, match="Alias SQL"):
        publication_scope_sql("x; DROP TABLE")


def test_additive_migration_does_not_move_legacy_or_erase_history():
    sql = (
        Path(__file__).resolve().parents[2]
        / "database" / "migrations" / "068_central_dispatch_compatibility.sql"
    ).read_text(encoding="utf-8").lower()
    assert "dispatch_mode text not null default 'legacy'" in sql
    assert "dispatch_cancelled_at timestamptz" in sql
    assert "dispatch_revision integer not null default 1" in sql
    assert "where dispatch_mode = 'central' and dispatch_cancelled_at is null" in sql
    assert "update public.schedulers" not in sql
    assert "delete from" not in sql
    assert "drop table" not in sql

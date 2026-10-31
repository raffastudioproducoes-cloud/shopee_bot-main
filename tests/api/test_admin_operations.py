"""Operational dashboard does not leak SQL or invent metrics when unavailable."""
import asyncio
from unittest.mock import MagicMock

from api import admin_operations


def test_operations_aggregates_are_typed_and_no_sql_is_exposed(monkeypatch):
    db = MagicMock()
    payload = {
        "collected_at": "2026-10-31T02:35:00+00:00",
        "database": {"active": 1, "idle": 10, "idle_in_transaction": 0, "blocked": 0, "max_connections": 60},
        "queries": {"tracked_statements": 1170, "slow_patterns": 8,
                    "worst": [{"rank": 1, "calls": 57, "mean_ms": 586.6,
                               "max_ms": 1200.3, "total_ms": 33437.6,
                               "query": "SELECT sensitive FROM password_table"}]},
        "uptime": {"status": "no_samples", "ok": 0, "error": 0,
                   "unanswered": 0, "latest": None, "latest_at": None, "recent": []},
    }
    acquisition = {"status": "available", "source": "self_reported",
                   "minimum_group_size": 3, "declared_total": 1, "groups": []}
    db.rpc.side_effect = lambda name: MagicMock(execute=lambda: MagicMock(
        data=acquisition if name == "admin_acquisition_aggregates" else payload))
    monkeypatch.setattr(admin_operations, "supabase", db)
    monkeypatch.delenv("ADMIN_ESTIMATED_MONTHLY_BRL", raising=False)
    result = asyncio.run(admin_operations.collect_operations())
    assert result.status == "available"
    assert result.queries.tracked_statements == 1170
    assert "SELECT sensitive" not in result.model_dump_json()
    assert result.costs.status == "not_configured"
    assert result.uptime.status == "no_samples"
    assert result.acquisition.groups == []


def test_estimates_require_explicit_nonnegative_budget(monkeypatch):
    for text in ("", "nan", "inf", "-10", "abc"):
        monkeypatch.setenv("ADMIN_ESTIMATED_MONTHLY_BRL", text)
        assert admin_operations._cost_model().status == "not_configured"
    monkeypatch.setenv("ADMIN_ESTIMATED_MONTHLY_BRL", "300")
    cost = admin_operations._cost_model()
    assert cost.status == "estimate"
    assert cost.monthly_brl == 300
    assert cost.daily_brl == 10


def test_rpc_failure_does_not_turn_unavailable_uptime_into_zero(monkeypatch):
    db = MagicMock()
    db.rpc.return_value.execute.side_effect = RuntimeError("secret-auth=private")
    monkeypatch.setattr(admin_operations, "supabase", db)
    result = asyncio.run(admin_operations.collect_operations())
    assert result.status == "unavailable"
    assert result.uptime is None
    assert "private" not in result.model_dump_json()

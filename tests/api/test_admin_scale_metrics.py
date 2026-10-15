"""Contrato de escala: somente agregados validados podem chegar ao ADMIN."""
import pytest
from pydantic import ValidationError

from api.admin_metrics import ScaleMetrics


def test_scale_metrics_whitelists_aggregates():
    result = ScaleMetrics.model_validate({"server_errors": 2, "p99_latency_ms": 98,
        "database": {"blocked_connections": 1, "oldest_transaction_seconds": 8,
                     "tables": [{"name": "posts", "table_bytes": 10, "index_bytes": 5, "sql": "private"}]},
        "user_id": "private"}).model_dump()
    assert "private" not in str(result)
    assert result["server_errors"] == 2


def test_scale_metrics_rejects_negative_and_nonfinite():
    for payload in [{"server_errors": -1}, {"p99_latency_ms": float("inf")},
                    {"database": {"blocked_connections": -1}}]:
        with pytest.raises(ValidationError):
            ScaleMetrics.model_validate(payload)

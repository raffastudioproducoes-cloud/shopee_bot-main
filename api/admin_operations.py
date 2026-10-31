"""Administrative operational telemetry, without raw SQL/user records."""
import asyncio
import logging
import os
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .database import supabase

logger = logging.getLogger(__name__)


class DbPerformance(BaseModel):
    active: int = Field(ge=0)
    idle: int = Field(ge=0)
    idle_in_transaction: int = Field(ge=0)
    blocked: int = Field(ge=0)
    max_connections: int = Field(gt=0)


class QueryPattern(BaseModel):
    rank: int = Field(ge=1)
    calls: int = Field(ge=0)
    mean_ms: float = Field(ge=0)
    max_ms: float = Field(ge=0)
    total_ms: float = Field(ge=0)


class QueryPerformance(BaseModel):
    tracked_statements: int = Field(ge=0)
    slow_patterns: int = Field(ge=0)
    worst: list[QueryPattern] = Field(default_factory=list, max_length=5)


class UptimeSample(BaseModel):
    at: datetime
    status: Literal["ok", "error", "unanswered"]


class UptimeHistory(BaseModel):
    status: Literal["sampled", "no_samples"]
    ok: int = Field(ge=0)
    error: int = Field(ge=0)
    unanswered: int = Field(ge=0)
    latest: Literal["ok", "error", "unanswered"] | None = None
    latest_at: datetime | None = None
    recent: list[UptimeSample] = Field(default_factory=list, max_length=48)


class CostModel(BaseModel):
    status: Literal["not_configured", "estimate"]
    monthly_brl: float | None = None
    daily_brl: float | None = None
    note: str = "Estimativa configurada pelo operador, não extraída de faturas ou cobrança confirmada."


class AcquisitionGroup(BaseModel):
    source: Literal["search","social","referral","direct","other"]
    accounts: int = Field(ge=3)


class AcquisitionMetrics(BaseModel):
    status: Literal["available", "unavailable"] = "unavailable"
    source: Literal["self_reported"] | None = None
    minimum_group_size: int = 3
    declared_total: int = Field(default=0, ge=0)
    groups: list[AcquisitionGroup] = Field(default_factory=list)


class OperationsResponse(BaseModel):
    status: Literal["available", "unavailable"]
    collected_at: datetime | None = None
    database: DbPerformance | None = None
    queries: QueryPerformance | None = None
    uptime: UptimeHistory | None = None
    costs: CostModel
    acquisition: AcquisitionMetrics = Field(default_factory=AcquisitionMetrics)


def _cost_model() -> CostModel:
    # Operator-configured monthly budget is never inferred from service plan or request duration.
    raw = os.getenv("ADMIN_ESTIMATED_MONTHLY_BRL", "").strip()
    try:
        n = float(raw)
        if 0 <= n <= 1_000_000 and n == n and n not in (float("inf"), float("-inf")):
            return CostModel(status="estimate", monthly_brl=round(n, 2), daily_brl=round(n / 30, 2))
    except (ValueError, TypeError):
        pass
    return CostModel(status="not_configured")


async def collect_operations() -> OperationsResponse:
    costs = _cost_model()
    async def get_acquisition() -> AcquisitionMetrics:
        try:
            response = await asyncio.wait_for(
                run_in_threadpool(lambda: supabase.rpc("admin_acquisition_aggregates").execute()),
                timeout=5,
            )
            return AcquisitionMetrics.model_validate(response.data)
        except Exception as exc:
            logger.warning("Aquisição agregada indisponível (%s)", type(exc).__name__)
            return AcquisitionMetrics()

    acquisition = await get_acquisition()
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(lambda: supabase.rpc("admin_operations_snapshot").execute()),
            timeout=8,
        )
        return OperationsResponse.model_validate({
            "status": "available", "costs": costs, "acquisition": acquisition, **result.data
        })
    except Exception as exc:
        # Exception messages could contain SQL, URLs or credentials: suppress them.
        logger.warning("Métricas operacionais indisponíveis (%s)", type(exc).__name__)
        return OperationsResponse(status="unavailable", costs=costs, acquisition=acquisition)

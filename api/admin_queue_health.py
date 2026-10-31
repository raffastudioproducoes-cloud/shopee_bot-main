"""Aggregate publication-queue health for administrators only.

Reads a service_role-only SQL function, never exposing post text, user IDs,
provider IDs, raw errors, claim tokens or credential details.
"""
import asyncio
import logging
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .database import supabase

logger = logging.getLogger("uvicorn.error")


class QueueCounts(BaseModel):
    total: int = Field(ge=0)
    pending: int = Field(ge=0)
    running: int = Field(ge=0)
    unknown: int = Field(ge=0)
    reported_removed: int = Field(default=0, ge=0)
    failed: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    manually_confirmed: int = Field(ge=0)
    multiple_attempts: int = Field(ge=0)


class QueueHealthResponse(BaseModel):
    status: Literal["available", "unavailable"]
    counts: QueueCounts | None = None
    oldest_unknown_minutes: int | None = Field(default=None, ge=0)
    oldest_running_minutes: int | None = Field(default=None, ge=0)
    last_started_at: datetime | None = None
    collected_at: datetime | None = None


async def collect_queue_health() -> QueueHealthResponse:
    """Isolated read. Failure never becomes a fabricated zero or broken admin page."""
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(
                lambda: supabase.rpc("admin_queue_health_snapshot").execute()
            ),
            timeout=6,
        )
        return QueueHealthResponse.model_validate({"status": "available", **result.data})
    except Exception as exc:
        # Never log exception messages; providers may include sensitive values.
        logger.warning("Fila administrativa indisponível (%s)", type(exc).__name__)
        return QueueHealthResponse(status="unavailable")

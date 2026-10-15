"""Observabilidade ADMIN: agregados explícitos, sem linhas pessoais ou segredos."""
import asyncio
import logging
import math
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Literal

import httpx
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .config import settings
from .database import supabase

logger = logging.getLogger("uvicorn.error")
Status = Literal["available", "partial", "unavailable", "not_configured"]


class Counts(BaseModel):
    accounts: int = Field(ge=0)
    new_accounts: int = Field(ge=0)
    deleted_accounts: int = Field(ge=0)
    free_accounts: int = Field(ge=0)
    plus_accounts: int = Field(ge=0)
    premium_accounts: int = Field(ge=0)
    active_accounts: int | None = Field(ge=0)
    requests: int = Field(ge=0)
    errors: int = Field(ge=0)
    avg_latency_ms: float | None = Field(ge=0, allow_inf_nan=False)
    p95_latency_ms: float | None = Field(ge=0, allow_inf_nan=False)


class DailyPoint(BaseModel):
    date: date
    registrations: int = Field(ge=0)
    deletions: int = Field(ge=0)
    requests: int = Field(ge=0)


class DatabaseValues(BaseModel):
    database_bytes: int = Field(ge=0)
    connections: int = Field(ge=0)
    max_connections: int = Field(gt=0)


class Snapshot(BaseModel):
    counts: Counts
    daily: list[DailyPoint] = Field(max_length=90)
    database: DatabaseValues


class SupabaseMetrics(BaseModel):
    status: Status
    database_bytes: int | None = None
    connections: int | None = None
    max_connections: int | None = None
    latency_ms: float | None = None


class ResourceMetric(BaseModel):
    value: float = Field(ge=0, allow_inf_nan=False)
    unit: str
    timestamp: datetime
    values: list[float]
    timestamps: list[datetime]


class RenderMetrics(BaseModel):
    status: Status
    cpu: ResourceMetric | None = None
    memory: ResourceMetric | None = None
    cpu_limit: ResourceMetric | None = None
    memory_limit: ResourceMetric | None = None
    bandwidth: ResourceMetric | None = None


class UnavailableMetrics(BaseModel):
    paying_accounts: str = "Cobrança ainda não integrada; plano cadastrado não confirma pagamento."
    traffic_sources: str = "Origem de tráfego não coletada."
    session_time: str = "Tempo de utilização não medido."
    location: str = "Localização não coletada; nenhum IP ou endereço é usado neste painel."


class AdminMetricsResponse(BaseModel):
    status: Status
    updated_at: datetime
    days: int
    counts: Counts | None
    daily: list[DailyPoint]
    supabase: SupabaseMetrics
    render: RenderMetrics
    unavailable: UnavailableMetrics
    notes: list[str]


async def _database_snapshot(days: int) -> tuple[Snapshot | None, float]:
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(run_in_threadpool(
            lambda: supabase.rpc("admin_metrics_snapshot", {"lookback_days": days}).execute()
        ), timeout=5)
        return Snapshot.model_validate(result.data), (time.perf_counter() - started) * 1000
    except Exception as exc:
        logger.warning("Métricas Supabase indisponíveis (%s)", type(exc).__name__)
        return None, (time.perf_counter() - started) * 1000


def parse_render_metric(payload: list[dict]) -> ResourceMetric | None:
    """Remove todos os labels/identificadores; soma instâncias no mesmo instante."""
    units = {series["unit"] for series in payload if series.get("values")}
    if not units:
        return None
    if len(units) != 1 or next(iter(units)) not in {"CPU", "cpu", "cores", "core", "bytes", "byte", "B", "mb", "MB", "GB", "MiB", "GiB", "%", "percent"}:
        raise ValueError("Unidade de métrica incompatível")
    points: dict[datetime, float] = {}
    for series in payload:
        for point in series.get("values", []):
            timestamp = datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("Amostra sem fuso horário")
            value = float(point["value"])
            if not math.isfinite(value) or value < 0:
                raise ValueError("Amostra inválida")
            points[timestamp] = points.get(timestamp, 0) + value
            if not math.isfinite(points[timestamp]):
                raise ValueError("Soma de amostras inválida")
    ordered = sorted(points)
    return ResourceMetric(value=points[ordered[-1]], unit=next(iter(units)), timestamp=ordered[-1], values=[points[t] for t in ordered], timestamps=ordered)


async def _render_snapshot() -> RenderMetrics:
    token = os.getenv("RENDER_METRICS_API_KEY")
    resource = os.getenv("RENDER_SERVICE_ID")
    if not token or not resource:
        return RenderMetrics(status="not_configured")
    end = datetime.now(timezone.utc)
    params = {"resource": resource, "resolutionSeconds": 3600, "startTime": (end - timedelta(hours=24)).isoformat(), "endTime": end.isoformat()}
    async with httpx.AsyncClient(timeout=httpx.Timeout(4, connect=2), follow_redirects=False) as client:
        async def fetch(kind: str) -> ResourceMetric | None:
            try:
                response = await client.get(f"https://api.render.com/v1/metrics/{kind}", params=params, headers={"Authorization": f"Bearer {token}"})
                response.raise_for_status()
                return parse_render_metric(response.json())
            except Exception as exc:
                logger.warning("Métrica Render %s indisponível (%s)", kind, type(exc).__name__)
                return None
        cpu, memory, cpu_limit, memory_limit, bandwidth = await asyncio.gather(*(fetch(kind) for kind in ("cpu", "memory", "cpu-limit", "memory-limit", "bandwidth")))
    metrics = (cpu, memory, cpu_limit, memory_limit, bandwidth)
    status: Status = "available" if all(metrics) else "partial" if any(metrics) else "unavailable"
    return RenderMetrics(status=status, cpu=cpu, memory=memory, cpu_limit=cpu_limit, memory_limit=memory_limit, bandwidth=bandwidth)


async def collect_admin_metrics(days: int) -> AdminMetricsResponse:
    (snapshot, latency), render = await asyncio.gather(_database_snapshot(days), _render_snapshot())
    notes = [
        "Ativos: contas com requisição autenticada nos últimos 5 minutos, não presença exata em tempo real.",
        "Cadastros: contas que ainda existem e foram criadas no período; excluídas não integram essa série.",
        "Exclusões: eventos preservados na auditoria disponível, não histórico anterior à coleta.",
        "Planos Free/Plus/Premium correspondem ao perfil principal, sem confirmação de pagamento.",
        "Tamanho do banco não equivale a disco total, armazenamento de arquivos ou cota faturável.",
    ]
    if snapshot and not settings.request_logging_enabled:
        snapshot.counts.active_accounts = None
        notes.append("Registro de requisições desativado: atividade recente indisponível e histórico de acessos incompleto.")
    supabase_metrics = SupabaseMetrics(status="available", latency_ms=round(latency, 1), **snapshot.database.model_dump()) if snapshot else SupabaseMetrics(status="unavailable")
    if not snapshot:
        notes.append("Métricas do banco indisponíveis; valide a migração de observabilidade antes de ativar o painel.")
    status: Status = "available" if snapshot and render.status == "available" else "partial" if snapshot or render.status in {"available", "partial"} else "unavailable"
    return AdminMetricsResponse(
        status=status, updated_at=datetime.now(timezone.utc), days=days,
        counts=snapshot.counts if snapshot else None, daily=snapshot.daily if snapshot else [],
        supabase=supabase_metrics, render=render, unavailable=UnavailableMetrics(), notes=notes,
    )

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
Diagnostic = Literal["timeout", "permission_denied", "rpc_missing", "invalid_response",
                     "provider_error", "api_rejected", "bad_request", "no_samples", "not_configured"]


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


class PreviousPeriod(BaseModel):
    starts_on: date
    ends_on: date
    registrations: int = Field(ge=0)
    deletions: int = Field(ge=0)
    requests: int = Field(ge=0)
    errors: int = Field(ge=0)


class TableSize(BaseModel):
    name: Literal["users", "profiles", "posts", "activities", "request_logs", "audit_events", "schedulers", "medias"]
    table_bytes: int = Field(ge=0)
    index_bytes: int = Field(ge=0)


class DatabaseHealth(BaseModel):
    blocked_connections: int = Field(default=0, ge=0)
    oldest_transaction_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    tables: list[TableSize] = Field(default_factory=list, max_length=8)


class Operations(BaseModel):
    scheduled: int = Field(ge=0)
    published_events: int = Field(ge=0)
    failed_events: int = Field(ge=0)
    publishing_accounts: int = Field(ge=0)


class Engagement(BaseModel):
    active_week: int = Field(ge=0)
    previous_week: int = Field(ge=0)
    returning_week: int = Field(ge=0)


class CapacityPoint(BaseModel):
    date: date
    database_bytes: int = Field(ge=0)
    observed_connections: int = Field(ge=0)


class PlanConsumption(BaseModel):
    plan: Literal["free", "plus", "premium", "unknown"]
    requests: int = Field(ge=0)
    request_duration_ms: int = Field(ge=0)


class ScaleMetrics(BaseModel):
    collected_at: datetime | None = None
    server_errors: int | None = Field(default=None, ge=0)
    rate_limited_requests: int | None = Field(default=None, ge=0)
    p99_latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    database: DatabaseHealth | None = None
    operations: Operations | None = None
    engagement: Engagement | None = None
    capacity_history: list[CapacityPoint] = Field(default_factory=list, max_length=90)
    consumption: list[PlanConsumption] = Field(default_factory=list, max_length=4)


class Snapshot(BaseModel):
    counts: Counts
    daily: list[DailyPoint] = Field(max_length=90)
    database: DatabaseValues
    previous_period: PreviousPeriod | None = None
    scale: ScaleMetrics | None = None


class SupabaseMetrics(BaseModel):
    status: Status
    diagnostic: Diagnostic | None = None
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
    diagnostic: Diagnostic | None = None
    missing_metrics: list[Literal["cpu", "memory", "cpu_limit", "memory_limit", "bandwidth"]] = Field(default_factory=list, max_length=5)
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


class GeographyRegion(BaseModel):
    region: str
    online: int = Field(ge=0)
    offline: int = Field(ge=0)
    deleted: int = Field(default=0, ge=0)


class GeographyMetrics(BaseModel):
    status: Literal["available", "not_configured"] = "not_configured"
    updated_at: datetime | None = None
    source: Literal["voluntary"] | None = None
    minimum_group_size: int = Field(default=3, ge=3)
    regions: list[GeographyRegion] = Field(default_factory=list, max_length=20)


class AdminMetricsResponse(BaseModel):
    status: Status
    updated_at: datetime
    days: int
    counts: Counts | None
    daily: list[DailyPoint]
    supabase: SupabaseMetrics
    render: RenderMetrics
    geography: GeographyMetrics = Field(default_factory=GeographyMetrics)
    unavailable: UnavailableMetrics
    notes: list[str]
    previous_period: PreviousPeriod | None = None
    scale: ScaleMetrics | None = None


def _safe_error(exc: Exception) -> str:
    """Tipo e, se houver, status HTTP numérico; nunca a mensagem (pode conter segredo)."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return f"{type(exc).__name__} status={status}" if isinstance(status, int) else type(exc).__name__


def _database_diagnostic(exc: Exception) -> Diagnostic:
    """Safe, bounded diagnostics: never include SQL, URLs, credentials or provider text."""
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "timeout"
    code = getattr(exc, "code", None)
    if isinstance(code, str):
        if code in ("42501", "PGRST301"):
            return "permission_denied"
        if code in ("42883", "PGRST202"):
            return "rpc_missing"
    if isinstance(exc, ValueError):
        return "invalid_response"
    return "provider_error"


async def _database_snapshot(days: int) -> tuple[Snapshot | None, float, Diagnostic | None]:
    started = time.perf_counter()
    try:
        # RPC occasionally takes longer than 5 seconds with 30/90-day aggregations.
        # Surface timeout separately rather than reporting false zeros.
        result = await asyncio.wait_for(run_in_threadpool(
            lambda: supabase.rpc("admin_metrics_snapshot", {"lookback_days": days}).execute()
        ), timeout=12)
        return Snapshot.model_validate(result.data), (time.perf_counter() - started) * 1000, None
    except Exception as exc:
        diagnostic = _database_diagnostic(exc)
        logger.warning("Métricas Supabase indisponíveis (%s; %s)", diagnostic, _safe_error(exc))
        return None, (time.perf_counter() - started) * 1000, diagnostic


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


# Métricas Render sempre do serviço de PRODUÇÃO (shopee-bot), inclusive quando
# o painel roda no staging. Ids de serviço não são segredos.
RENDER_PRODUCTION_SERVICE_ID = "srv-da6vrla6iojc7380a13g"
RENDER_STAGING_SERVICE_ID = "srv-daukgs17lnhs738tpl50"


def _render_service_id() -> str:
    configured = os.getenv("RENDER_ADMIN_SERVICE_ID", "").strip()
    if not configured or configured == RENDER_STAGING_SERVICE_ID:
        return RENDER_PRODUCTION_SERVICE_ID
    return configured


def _render_token() -> str:
    return (os.getenv("RENDER_METRICS_API_KEY") or os.getenv("RENDER_API_KEY") or "").strip()


async def _render_snapshot() -> RenderMetrics:
    token = _render_token()
    resource = _render_service_id()
    if not token:
        return RenderMetrics(status="not_configured", diagnostic="not_configured")
    # Start with the documented minimum query: resource only. The Render API
    # supplies the last hour by default. Optional time/resolution parameters
    # previously triggered HTTP 400 for all five endpoints.
    params = {"resource": resource}
    async with httpx.AsyncClient(timeout=httpx.Timeout(4, connect=2), follow_redirects=False) as client:
        async def fetch(kind: str) -> tuple[ResourceMetric | None, Diagnostic | None]:
            try:
                response = await client.get(f"https://api.render.com/v1/metrics/{kind}", params=params, headers={"Authorization": f"Bearer {token}"})
                response.raise_for_status()
                metric = parse_render_metric(response.json())
                return metric, None if metric else "no_samples"
            except httpx.HTTPStatusError as exc:
                diagnostic: Diagnostic = (
                    "api_rejected" if exc.response.status_code in (401, 403) else
                    "bad_request" if exc.response.status_code == 400 else "provider_error"
                )
                logger.warning("Métrica Render %s indisponível (%s; %s)", kind, diagnostic, _safe_error(exc))
                return None, diagnostic
            except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
                logger.warning("Métrica Render %s indisponível (%s)", kind, _safe_error(exc))
                return None, "timeout"
            except Exception as exc:
                logger.warning("Métrica Render %s indisponível (%s)", kind, _safe_error(exc))
                return None, "provider_error"
        results = await asyncio.gather(*(fetch(kind) for kind in ("cpu", "memory", "cpu-limit", "memory-limit", "bandwidth")))
    metrics = tuple(value for value, _ in results)
    cpu, memory, cpu_limit, memory_limit, bandwidth = metrics
    missing_names = ("cpu", "memory", "cpu_limit", "memory_limit", "bandwidth")
    missing = [name for name, metric in zip(missing_names, metrics) if metric is None]
    errors = [reason for _, reason in results if reason]
    priority = ("api_rejected", "bad_request", "timeout", "provider_error", "no_samples")
    diagnostic = next((reason for reason in priority if reason in errors), None)
    status: Status = "available" if all(metrics) else "partial" if any(metrics) else "unavailable"
    return RenderMetrics(status=status, diagnostic=diagnostic, missing_metrics=missing,
                         cpu=cpu, memory=memory, cpu_limit=cpu_limit, memory_limit=memory_limit, bandwidth=bandwidth)


async def collect_admin_metrics(days: int) -> AdminMetricsResponse:
    async def read_geography() -> GeographyMetrics:
        try:
            response = await asyncio.wait_for(
                run_in_threadpool(lambda: supabase.rpc("admin_region_aggregates").execute()),
                timeout=5,
            )
            return GeographyMetrics.model_validate(response.data)
        except Exception as exc:
            logger.warning("Agregação geográfica indisponível (%s)", type(exc).__name__)
            return GeographyMetrics()

    (snapshot, latency, db_diagnostic), render, geography = await asyncio.gather(
        _database_snapshot(days), _render_snapshot(), read_geography()
    )
    if snapshot and snapshot.scale:
        snapshot.scale.collected_at = datetime.now(timezone.utc)
    notes = [
        "Ativos: contas com requisição autenticada nos últimos 5 minutos, não presença exata em tempo real.",
        "Cadastros: contas que ainda existem e foram criadas no período; excluídas não integram essa série.",
        "Exclusões: eventos preservados na auditoria disponível, não histórico anterior à coleta.",
        "Planos Free/Plus/Premium correspondem ao perfil principal, sem confirmação de pagamento.",
        "Tamanho do banco não equivale a disco total, armazenamento de arquivos ou cota faturável.",
        "Comparação: período atual inclui hoje incompleto; anterior contém o mesmo número de dias completos.",
    ]
    if snapshot and not settings.request_logging_enabled:
        snapshot.counts.active_accounts = None
        if snapshot.scale:
            snapshot.scale.engagement = None
            snapshot.scale.server_errors = None
            snapshot.scale.rate_limited_requests = None
            snapshot.scale.p99_latency_ms = None
            snapshot.scale.consumption = []
        notes.append("Registro de requisições desativado: atividade recente indisponível e histórico de acessos incompleto.")
    supabase_metrics = SupabaseMetrics(status="available", latency_ms=round(latency, 1), **snapshot.database.model_dump()) if snapshot else SupabaseMetrics(status="unavailable", diagnostic=db_diagnostic, latency_ms=round(latency, 1))
    if not snapshot:
        notes.append("Métricas do banco indisponíveis; valide a migração de observabilidade antes de ativar o painel.")
    status: Status = "available" if snapshot and render.status == "available" else "partial" if snapshot or render.status in {"available", "partial"} else "unavailable"
    return AdminMetricsResponse(
        status=status, updated_at=datetime.now(timezone.utc), days=days,
        counts=snapshot.counts if snapshot else None, daily=snapshot.daily if snapshot else [],
        supabase=supabase_metrics, render=render, geography=geography,
        unavailable=UnavailableMetrics(), notes=notes,
        previous_period=snapshot.previous_period if snapshot else None,
        scale=snapshot.scale if snapshot else None,
    )

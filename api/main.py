"""
Auto Orbital — API Python (FastAPI)
Consome Supabase existente. Coexiste com Flask durante a migração.
"""

import asyncio
import os
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from .config import settings
from . import rate_limit_store
from .database import get_supabase, init_db
from .middleware import AccessLogRedactor, RequestIDMiddleware, RequestLoggingMiddleware
from .routers.posts import cleanup_expired_media_drafts
from .routers.auth import cleanup_expired_sessions
from .routers.admin import router as admin_router
from .plan_grants import expire_due_grants

for noisy_logger in ("httpx", "httpcore", "urllib3"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

logging.getLogger("uvicorn.access").addFilter(AccessLogRedactor())

logger = logging.getLogger("uvicorn.error")
_ready_cache = (0.0, False)
from .routers import (
    auth_router,
    supabase_auth_router,
    catalog_router,
    products_router,
    product_media_router,
    lists_router,
    campaigns_router,
    posts_router,
    credentials_router,
    users_router,
    dashboard_router,
    social_analytics_router,
    notifications_router,
    profiles_router,
    settings_router,
    meta_callbacks_router,
)
from .routers.billing import admin_router as billing_admin_router, router as billing_router
from .routers.platform_ai import router as platform_ai_router
from .routers.platform_shopee import router as platform_shopee_router
from .routers.shopee_video import router as shopee_video_router
from .routers.post_metrics import router as post_metrics_router
from .routers.link_redirect import router as link_redirect_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Substitui os antigos @app.on_event("startup"/"shutdown") (deprecados);
    # o comportamento de startup() e shutdown() permanece o mesmo.
    await startup()
    try:
        yield
    finally:
        await shutdown()


app = FastAPI(
    lifespan=lifespan,
    title="Auto Orbital API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-CSRFToken", "X-CSRF-Token", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(APIError)
async def _postgrest_no_rows_as_404(request, exc: APIError):
    """`.single()` sem linha vira 404 (não 500).

    O PostgREST responde PGRST116 quando `.single()` não acha nenhuma linha. Isso acontece
    de propósito quando o filtro de dono (S-01) esconde o recurso de outra conta; a resposta
    correta é a mesma de "não existe", sem vazar a diferença. Qualquer outro erro do banco
    (inclusive "mais de uma linha") continua sendo 500.
    """
    if getattr(exc, "code", None) == "PGRST116" and "0 rows" in str(getattr(exc, "details", "") or ""):
        return JSONResponse(status_code=404, content={"detail": "Recurso não encontrado"})
    logger.error("Erro do banco (%s): %s", getattr(exc, "code", None), getattr(exc, "message", ""))
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# Routers
app.include_router(auth_router)
app.include_router(supabase_auth_router)
app.include_router(admin_router)
# catalog_router ANTES de products_router: registra rotas literais
# "/products/catalog-search" e "/products/catalog-categories" — se
# products_router (com "/products/{product_id}") for registrado primeiro,
# o Starlette casa o path pattern primeiro e falha a validação de
# product_id:int antes de tentar a rota literal (mesmo cuidado de ordem de
# registro documentado em credentials.py pra rotas literais vs "/{network}").
app.include_router(catalog_router)
app.include_router(product_media_router)
app.include_router(products_router)
app.include_router(lists_router)
app.include_router(campaigns_router)
app.include_router(posts_router)
app.include_router(credentials_router)
app.include_router(platform_ai_router)
app.include_router(platform_shopee_router)
app.include_router(shopee_video_router)
app.include_router(users_router)
app.include_router(dashboard_router)
app.include_router(social_analytics_router)
app.include_router(post_metrics_router)
app.include_router(link_redirect_router)
app.include_router(notifications_router)
app.include_router(profiles_router)
app.include_router(settings_router)
app.include_router(meta_callbacks_router)
app.include_router(billing_router)
app.include_router(billing_admin_router)


async def _cleanup_media_drafts_periodically() -> None:
    """Best effort: cada worker remove rascunhos e sessoes vencidas a cada hora."""
    while True:
        try:
            await run_in_threadpool(cleanup_expired_media_drafts)
        except Exception:
            logger.warning("Falha na limpeza periódica de rascunhos de mídia", exc_info=True)
        try:
            await run_in_threadpool(cleanup_expired_sessions)
        except Exception:
            logger.warning("Falha na limpeza periódica de sessões vencidas", exc_info=True)
        await asyncio.sleep(3600)


async def _expire_plan_grants_periodically() -> None:
    """Best effort: concessões de plano vencidas voltam ao Free em até 5 minutos."""
    while True:
        try:
            await run_in_threadpool(expire_due_grants)
        except Exception:
            logger.warning("Falha na expiração periódica de concessões de plano", exc_info=True)
        await asyncio.sleep(300)


# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health/ready")
async def health_ready():
    global _ready_cache
    cached_at, cached_ok = _ready_cache
    if time.monotonic() - cached_at < 3:
        return {"status": "ok"} if cached_ok else JSONResponse({"status": "not_ready"}, status_code=503)
    try:
        await asyncio.wait_for(run_in_threadpool(lambda: get_supabase().table("users").select("id").limit(1).execute()), 1.0)
        _ready_cache = (time.monotonic(), True)
    except Exception as exc:
        _ready_cache = (time.monotonic(), False)
        logger.warning("Health check do banco falhou (%s)", type(exc).__name__)
        return JSONResponse({"status": "not_ready"}, status_code=503)
    return {"status": "ok"}


def _log_rate_limit_mode() -> None:
    try:
        workers = int(os.environ.get("WEB_CONCURRENCY", "1") or 1)
    except ValueError:
        workers = 1
    level, message = rate_limit_store.describe_mode(workers)
    getattr(logger, level)(message)


async def startup():
    _log_rate_limit_mode()
    # init_db() nunca pode deixar exceção subir daqui: esse handler roda no
    # subprocesso uvicorn separado (gunicorn.conf.py::on_starting) e, se ele
    # morrer com o processo inteiro (sys.exit no lifespan), o gunicorn.conf.py
    # já isola isso do Flask — mas rotas continuarem de pé mesmo sem Supabase
    # configurado é estritamente melhor (falha por rota, não o processo
    # inteiro). Ver api/database.py::get_supabase para o RuntimeError.
    try:
        init_db()
    except RuntimeError as exc:
        logger.error(
            "FastAPI subiu sem Supabase configurado (%s). Rotas que dependem "
            "do Supabase vao falhar com 500 ate SUPABASE_URL/SUPABASE_KEY "
            "serem definidas no ambiente.",
            exc,
        )
        return
    app.state.media_draft_cleanup_task = asyncio.create_task(_cleanup_media_drafts_periodically())
    app.state.plan_grant_expiry_task = asyncio.create_task(_expire_plan_grants_periodically())


async def shutdown():
    for name in ("media_draft_cleanup_task", "plan_grant_expiry_task"):
        task = getattr(app.state, name, None)
        if task:
            task.cancel()

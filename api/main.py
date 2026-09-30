"""
Shopee Auto Vendas — API Python (FastAPI)
Consome Supabase existente. Coexiste com Flask durante a migração.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .middleware import RequestLoggingMiddleware

logger = logging.getLogger("uvicorn.error")
from .routers import (
    auth_router,
    catalog_router,
    products_router,
    lists_router,
    posts_router,
    credentials_router,
    users_router,
    dashboard_router,
    notifications_router,
    logs_router,
)

app = FastAPI(
    title="Shopee Auto Vendas API",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

# Routers
app.include_router(auth_router)
# catalog_router ANTES de products_router: registra rotas literais
# "/products/catalog-search" e "/products/catalog-categories" — se
# products_router (com "/products/{product_id}") for registrado primeiro,
# o Starlette casa o path pattern primeiro e falha a validação de
# product_id:int antes de tentar a rota literal (mesmo cuidado de ordem de
# registro documentado em credentials.py pra rotas literais vs "/{network}").
app.include_router(catalog_router)
app.include_router(products_router)
app.include_router(lists_router)
app.include_router(posts_router)
app.include_router(credentials_router)
app.include_router(users_router)
app.include_router(dashboard_router)
app.include_router(notifications_router)
app.include_router(logs_router)


# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
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

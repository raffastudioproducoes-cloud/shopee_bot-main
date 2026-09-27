"""
Shopee Auto Vendas — API Python (FastAPI)
Consome Supabase existente. Coexiste com Flask durante a migração.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db

logger = logging.getLogger("uvicorn.error")
from .routers import (
    auth_router,
    products_router,
    lists_router,
    posts_router,
    credentials_router,
    users_router,
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

# Routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(lists_router)
app.include_router(posts_router)
app.include_router(credentials_router)
app.include_router(users_router)


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

"""
Shopee Auto Vendas — API Python (FastAPI)
Consome Supabase existente. Coexiste com Flask durante a migração.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import auth_router
from .routers.panel import router as panel_router

app = FastAPI(
    title="Shopee Auto Vendas API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
app.include_router(panel_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

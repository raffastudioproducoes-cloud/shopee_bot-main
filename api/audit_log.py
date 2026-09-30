"""
Log de passo de negócio explícito (ex: "iniciou OAuth do Instagram",
"token trocado", "post publicado") — reusa a tabela `request_logs` e o
mesmo flag `REQUEST_LOGGING_ENABLED` do middleware de requisição HTTP
(api/middleware.py), só preenchendo a coluna `action` (migração 032) em
vez de method/path.

Nunca levanta exceção pro chamador: é auxiliar, igual o middleware
(mesmo padrão de try/except + log.warning).
"""

import logging
from datetime import datetime, timezone

from .config import settings
from .database import get_supabase
from .utils.log_sanitizer import sanitize_log_data

logger = logging.getLogger("uvicorn.error")

_MAX_TEXT_LEN = 2000


def log_action(
    action: str,
    message: str | None = None,
    *,
    user_id: int | None = None,
    username: str | None = None,
) -> None:
    """Grava um passo de negócio em request_logs.action.

    `message` passa por sanitize_log_data ANTES de ir pro banco (defesa
    em profundidade nº1 — a nº2 é no GET /logs, ver api/routers/logs.py).
    Desligado junto com REQUEST_LOGGING_ENABLED=false (mesmo flag do
    middleware) — não faz sentido logar passo de negócio se o histórico
    de requisição também está desligado.
    """
    if not settings.request_logging_enabled:
        return

    try:
        supabase = get_supabase()
        safe_message = sanitize_log_data(message)[:_MAX_TEXT_LEN] if message else None
        supabase.table("request_logs").insert(
            {
                "user_id": user_id,
                "username": username,
                "method": "ACTION",
                "path": action,
                "action": action,
                "error": safe_message,
                "status_code": None,
                "duration_ms": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception:
        logger.warning("Falha ao gravar audit log de negócio (não crítico)", exc_info=True)

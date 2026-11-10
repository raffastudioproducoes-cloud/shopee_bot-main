"""Retenção de `request_logs`: remove registros com mais de 90 dias.

Decisão do dono (10/11/2026) e texto correspondente na Política de Privacidade (seção 6).
Só toca em `request_logs`; `audit_events` e dados da conta não são afetados. A exclusão é
feita em blocos pequenos para não estourar o tempo limite do PostgREST e é idempotente:
staging e produção compartilham o banco e podem rodar a rotina sem conflito.
"""
import logging
from datetime import datetime, timedelta, timezone

from .database import supabase

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90
BATCH_SIZE = 500
MAX_BATCHES = 40  # no máximo 20 mil linhas por execução; o restante sai na próxima


def retention_cutoff(now=None, days=RETENTION_DAYS):
    return (now or datetime.now(timezone.utc)) - timedelta(days=days)


def purge_old_request_logs(now=None):
    """Apaga logs mais antigos que RETENTION_DAYS. Devolve quantas linhas removeu."""
    cutoff = retention_cutoff(now).isoformat()
    removed = 0
    for _ in range(MAX_BATCHES):
        rows = (supabase.table("request_logs").select("id")
                .lt("created_at", cutoff).order("id").limit(BATCH_SIZE).execute())
        ids = [row["id"] for row in (rows.data or [])]
        if not ids:
            break
        supabase.table("request_logs").delete().in_("id", ids).execute()
        removed += len(ids)
        if len(ids) < BATCH_SIZE:
            break
    if removed:
        logger.info("Retenção de logs: %s registros com mais de %s dias removidos", removed, RETENTION_DAYS)
    return removed


def run_log_retention():
    """Ponto de entrada do agendador: nunca propaga exceção."""
    try:
        return purge_old_request_logs()
    except Exception:
        logger.exception("Falha na retenção de request_logs")
        return 0

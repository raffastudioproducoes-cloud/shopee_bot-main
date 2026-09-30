"""
Auditoria imutável de alterações sensíveis (preço, exclusão, dado sensível).

Grava em `audit_events` (migração 034) — diferente de `api/audit_log.py`
(passo de negócio em `request_logs`, ex: "iniciou OAuth"). Aqui é rastro de
MUDANÇA de dado: entidade, quem, quando, ação, valor antes/depois.

Mesmo padrão defensivo do audit_log.py: nunca levanta exceção pro chamador,
loga warning se falhar. Chame DEPOIS que a operação principal já teve
sucesso — falha de auditoria nunca deve derrubar a operação principal.
"""

import logging

from .database import supabase
from .utils.log_sanitizer import sanitize_log_data

logger = logging.getLogger("uvicorn.error")


def record_audit_event(
    entity: str,
    entity_id: str,
    user_id: str,
    action: str,
    old_value: dict | None,
    new_value: dict | None,
) -> None:
    """Grava um evento de auditoria em `audit_events`.

    `old_value`/`new_value` passam por `sanitize_log_data` antes de ir
    pro banco (reusa a mesma sanitização de `api/audit_log.py`, não
    duplica a lógica).
    """
    try:
        supabase.table("audit_events").insert({
            "entity": entity,
            "entity_id": entity_id,
            "user_id": user_id,
            "action": action,
            "old_value": sanitize_log_data(old_value),
            "new_value": sanitize_log_data(new_value),
        }).execute()
    except Exception:
        logger.warning("Falha ao gravar audit event (não crítico)", exc_info=True)

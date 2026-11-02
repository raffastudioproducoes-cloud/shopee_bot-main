"""Regra pura de edição de ocorrências futuras do Auto Orbital.

Não altera posts ou agendas. A aplicação da regra precisa ocorrer em transação,
junto ao claim, para impedir corrida com o executor no limite de 30 minutos.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

EDIT_LOCK_LEAD = timedelta(minutes=30)
IMMUTABLE_STATES = frozenset({
    "running", "succeeded", "published", "failed", "unknown",
    "manual_confirmed", "reported_removed", "cancelled",
})


@dataclass(frozen=True)
class EditWindow:
    allowed: bool
    reason: str
    locked_at: datetime


def occurrence_edit_window(
    scheduled_at: datetime,
    *,
    now: datetime,
    status: str = "pending",
    claimed: bool = False,
) -> EditWindow:
    """Editável só antes de T−30m, se não houver claim ou desfecho.

    Exatamente trinta minutos para o disparo já é bloqueado. Nunca muda um
    snapshot executado. Datas devem ser aware; a comparação é feita em UTC.
    """
    if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
        raise ValueError("scheduled_at deve incluir fuso horário")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now deve incluir fuso horário")
    instant = scheduled_at.astimezone(timezone.utc)
    current = now.astimezone(timezone.utc)
    lock_at = instant - EDIT_LOCK_LEAD
    if status in IMMUTABLE_STATES or status != "pending" or claimed:
        return EditWindow(False, "Ocorrência já iniciada, encerrada ou reivindicada.", lock_at)
    if current >= lock_at:
        return EditWindow(False, "Faltam 30 minutos ou menos para a publicação.", lock_at)
    return EditWindow(True, "Alterações permitidas somente nesta ocorrência futura.", lock_at)

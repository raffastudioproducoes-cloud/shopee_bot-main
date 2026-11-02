"""Contratos puros da transição F0 para o publicador único.

O gate começa DESLIGADO em todos os ambientes. Ativá-lo exige migration 068,
executor/reconciliador completo, testes e rollout coordenado. Nenhuma função
deste módulo cria job, publica, consulta segredos ou altera o banco.
"""

import os

from shopee_bot.database.scheduler_environment import (
    current_environment,
    publication_executor_environment,
)


_FLAG = "ORBITAL_CENTRAL_DISPATCH_ENABLED"
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"", "0", "false", "no", "off"})


def central_dispatch_enabled() -> bool:
    """Fail-closed: flags desconhecidas não podem ativar o executor."""
    raw = os.environ.get(_FLAG, "false").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ValueError(f"{_FLAG} inválida; use true ou false")


def new_schedule_dispatch_mode() -> str:
    """Legado até o gate ser explicitamente liberado."""
    return "central" if central_dispatch_enabled() else "legacy"


def can_execute_schedule(
    *, source_environment: str, dispatch_mode: str, cancelled: bool = False,
) -> bool:
    """Política de autoridade; não representa uma execução real.

    Legacy nunca muda de dono, inclusive os cinco cron de staging ainda
    ativos. Central fica reservado à produção quando o gate estiver ligado.
    """
    environment = current_environment()
    if cancelled:
        return False
    if dispatch_mode == "legacy":
        return source_environment == environment
    if dispatch_mode == "central":
        return central_dispatch_enabled() and (
            environment == publication_executor_environment()
        )
    return False


def publication_scope_sql(alias: str = "schedule") -> tuple[str, tuple[str, ...]]:
    """Predicado seguro para leituras/claims futuros; alias interno validado.

    O modo desativado mantém exatamente o filtro do scheduler atual.
    Quando habilitado, produção aceita legacy de produção OU central
    ativa de ambas as origens; staging só conserva seu legado local.
    """
    if alias not in {"schedule", "s"}:
        raise ValueError("Alias SQL não permitido")

    environment = current_environment()
    if not central_dispatch_enabled():
        return f"{alias}.environment = %s", (environment,)

    if environment == publication_executor_environment():
        return (
            f"(({alias}.environment = %s AND {alias}.dispatch_mode = 'legacy') "
            f"OR ({alias}.dispatch_mode = 'central' "
            f"AND {alias}.dispatch_cancelled_at IS NULL))",
            (environment,),
        )
    return (
        f"({alias}.environment = %s AND {alias}.dispatch_mode = 'legacy')",
        (environment,),
    )

"""Plano efetivo da conta: única fonte para decidir qual plano vale em checagens e respostas.

Conta ADMIN é sempre Premium com tudo liberado; `users.plan_tier` e `campaign_*` não
decidem nada para ela. Legado "plus" vale como "pro".
"""


def effective_plan(access: str | None, plan_tier: str | None) -> str | None:
    """Retorna "premium" para ADMIN; senão o plano gravado normalizado (None se ausente)."""
    if access == "ADMIN":
        return "premium"
    return "pro" if plan_tier == "plus" else plan_tier

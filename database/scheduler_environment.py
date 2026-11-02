"""Identidade da instância para executar jobs no Supabase compartilhado.

No Render, o branch injetado pela plataforma é a fonte autoritativa;
não confiar em uma variável configurável que poderia apontar staging para
a fila da produção. Fora do Render, o ambiente pode ser escolhido em teste.
"""
import os


def current_environment() -> str:
    if os.environ.get("RENDER", "").strip().lower() == "true":
        branch = os.environ.get("RENDER_GIT_BRANCH", "").strip()
        if branch == "main":
            return "production"
        if branch == "staging":
            return "staging"
        raise RuntimeError(
            "Branch Render sem ambiente de scheduler autorizado; "
            "somente main e staging podem executar publicações"
        )

    environment = os.environ.get("SCHEDULER_ENVIRONMENT", "production").strip().lower()
    if environment not in {"production", "staging"}:
        raise RuntimeError("SCHEDULER_ENVIRONMENT deve ser production ou staging")
    return environment

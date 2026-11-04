"""Visão geral da conta: contagens e resumos somente leitura.

O dashboard agrega todos os perfis da conta, inclusive histórico com
profile_id NULL. Os endpoints operacionais continuam isolados por perfil.
"""

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .auth import get_current_user_id
from ..database import supabase
from ..profiles import scope_account

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_LIMIT = 5
TEXT_PREVIEW_LIMIT = 160

# Espelho deliberado do enum database/activity_types.py: importar o módulo
# legado inicializaria dependências Flask/Postgres na API nova.
ACTIVITY_LABELS = {
    1: "Publicação concluída",
    2: "Falha na publicação",
    3: "Reinicialização concluída",
    4: "Falha na reinicialização",
    5: "Conexão realizada",
    6: "Falha na conexão",
    7: "Agendamento iniciado",
    8: "Agendamento concluído",
    9: "Falha no agendamento",
    10: "Informação do agendamento",
}


def _count(table: str, user_id: str, **filters: str) -> int:
    """Conta exata por conta; ausência de contagem não significa zero."""
    query = scope_account(
        supabase.table(table).select("id", count="exact"), user_id
    )
    for column, value in filters.items():
        query = query.is_(column, value)
    result = query.limit(1).execute()
    if result.count is None:
        raise ValueError("Contagem indisponível")
    return result.count


def _recent_rows(table: str, fields: str, user_id: str, *, roots: bool = False) -> list:
    query = scope_account(supabase.table(table).select(fields), user_id)
    if roots:
        query = query.is_("post_id", "null")
    result = (
        query.order("created_at", desc=True).order("id", desc=True)
        .limit(RECENT_LIMIT).execute()
    )
    if not isinstance(result.data, list):
        raise ValueError("Leitura indisponível")
    return result.data


def _load_stats(user_id: str) -> dict:
    counts = {
        "products_count": _count("products", user_id),
        "posts_count": _count("posts", user_id, post_id="null"),
        "lists_count": _count("product_lists", user_id),
        "scheduled_posts": _count("schedulers", user_id),
    }
    posts = _recent_rows("posts", "id,text,network,created_at", user_id, roots=True)
    activities = _recent_rows("activities", "id,activity_id,created_at", user_id)
    return {
        **counts,
        "recent_posts": [{
            "id": row["id"],
            "text_preview": " ".join((row.get("text") or "").split())[:TEXT_PREVIEW_LIMIT],
            "network": row.get("network") or "",
            "created_at": row.get("created_at"),
        } for row in posts],
        "recent_activities": [{
            "id": row["id"],
            "label": ACTIVITY_LABELS.get(row.get("activity_id"), "Atividade registrada"),
            "created_at": row.get("created_at"),
        } for row in activities],
    }


@router.get("/stats")
async def get_stats(user_id: str = Depends(get_current_user_id)):
    """Resumo autenticado por user_id, sem depender do perfil ativo.

    Não carrega metadata de atividades, mídia, credenciais ou dados de perfil.
    Falha de uma fonte invalida o resumo: nunca apresentar vazio/zero fictício.
    Não altera posts, agendas, jobs ou o banco compartilhado.
    """
    try:
        return await run_in_threadpool(_load_stats, user_id)
    except Exception:
        raise HTTPException(
            status_code=503, detail="Não foi possível carregar a visão geral da conta."
        ) from None

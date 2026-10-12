"""
Dashboard Router — API Python (FastAPI)

Contadores agregados pro card inicial do painel (DashboardPage.tsx). Nunca
existiu no backend migrado — o frontend sempre chamou `/dashboard/stats`
mas nenhum router respondia por esse prefixo, então a rota sempre voltava
404 e a página de dashboard inteira caía no branch de erro.
"""

from fastapi import APIRouter, Depends

from .auth import get_current_user_id
from .profiles import get_current_profile_id
from ..database import supabase
from ..profiles import scope_account, scope_owner

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _count(
    table: str,
    user_id: int,
    profile_id: str | None = None,
    *,
    account_owned: bool = False,
    **filters: str,
) -> int:
    """Conta linhas de `table` para o usuário sem baixar os dados
    (`count="exact"` + `limit(1)`: Postgrest calcula o total via
    Content-Range mesmo com o resultado limitado a 1 linha)."""
    base_query = supabase.table(table).select("id", count="exact")
    query = (
        scope_account(base_query, user_id)
        if account_owned
        else scope_owner(base_query, user_id, profile_id)
    )
    for column, value in filters.items():
        query = query.is_(column, value)
    result = query.limit(1).execute()
    return result.count or 0


@router.get("/stats")
async def get_stats(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Contagens do dashboard: produtos, posts (threads completas, não
    cada parte — mesmo critério de `posts.list_posts`: `post_id IS NULL`),
    listas de produtos e posts com agendamento ativo. Com perfil ativo, conta
    só o que pertence a ele. Produtos pertencem à conta e permanecem
    compartilhados entre perfis; sem perfil (token antigo), tudo da conta."""
    return {
        "products_count": _count("products", user_id, account_owned=True),
        "posts_count": _count("posts", user_id, profile_id, post_id="null"),
        "lists_count": _count("product_lists", user_id, profile_id),
        "scheduled_posts": _count("schedulers", user_id, profile_id),
    }

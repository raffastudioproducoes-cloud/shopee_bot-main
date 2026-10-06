"""
Notifications Router — API Python (FastAPI)

Expõe `activities` (log de eventos do bot/scheduler — ver
database/migrations/006_create_activities_table.sql) como notificações pro
sino do TopBar. Essa tabela já existia e era usada pelo painel Flask legado
(web/routes/activities.py) mas nunca tinha sido exposta pela API nova — o
sino no frontend React era só decoração (ícone sem onClick, bolinha de "não
lido" fixa via prop default, sem endpoint por trás).

Não há coluna de "lido/não lido" na tabela — o cliente decide o que é novo
comparando `created_at` com o timestamp da última vez que abriu o dropdown
(guardado no localStorage, ver frontend/src/stores/notificationsStore.ts).
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from .auth import get_current_user_id
from .profiles import get_current_profile_id
from ..database import supabase
from ..profiles import scope_owner

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    activity_type = row.get("activity_types") or {}
    return {
        "id": row["id"],
        "type": activity_type.get("name"),
        "description": activity_type.get("description"),
        "metadata": row.get("metadata") or {},
        "created_at": row["created_at"],
    }


@router.get("")
async def list_notifications(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
    cursor: str | None = Query(None, description="Cursor de paginação (created_at)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Lista atividades do usuário, mais recente primeiro, paginação por cursor."""
    query = (
        scope_owner(
            supabase.table("activities")
            .select("id, metadata, created_at, activity_types(name, description)"),
            user_id, profile_id,
        )
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)

    result = query.execute()
    rows = result.data or []

    next_cursor = None
    if rows and len(rows) == limit:
        next_cursor = rows[-1]["created_at"]

    return {"data": [_serialize(row) for row in rows], "next_cursor": next_cursor}

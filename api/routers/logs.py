"""
Logs Router — API Python (FastAPI)

Página de auditoria admin-only (pedido do dono do projeto: "capturar
todos os passos e funções que o aplicativo fizer, tirando senhas e
dados sensíveis"). Lê de `request_logs` (mesma tabela do middleware de
requisição, api/middleware.py, e do log de negócio, api/audit_log.py —
ver migração 032 pra coluna `action`).

Paginado via limit/offset (tabela já passa de 400 linhas — nunca
devolver tudo de uma vez). Sanitiza de novo antes de servir (defesa em
profundidade: api/audit_log.py já sanitiza antes de gravar, mas uma
linha de requisição HTTP normal, ex: `error` com traceback cru, nunca
passou por lá).
"""

from datetime import datetime
from uuid import UUID

from fastapi import Query

from ..database import supabase
from ..utils.log_sanitizer import sanitize_log_data

_FIELDS = "id, user_id, profile_id, username, method, path, action, status_code, duration_ms, error, redirect_to, created_at"


# Autorização (ADMIN) é aplicada pelo router em api/routers/admin.py.
async def list_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    # IDs de usuário são UUID (users.id) — `int` aqui rejeitava todo filtro real.
    user_id: UUID | None = Query(None, description="UUID do usuário"),
    profile_id: str | None = Query(None, description="Filtra por perfil (opcional)"),
    username: str | None = Query(None),
    status_code: int | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
):
    query = supabase.table("request_logs").select(_FIELDS, count="exact")

    if user_id is not None:
        query = query.eq("user_id", str(user_id))
    if profile_id:
        query = query.eq("profile_id", profile_id)
    if username:
        query = query.ilike("username", f"%{username}%")
    if status_code is not None:
        query = query.eq("status_code", status_code)
    if created_from is not None:
        query = query.gte("created_at", created_from.isoformat())
    if created_to is not None:
        query = query.lte("created_at", created_to.isoformat())

    result = (
        query.order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    rows = [sanitize_log_data(row) for row in (result.data or [])]
    total = result.count if result.count is not None else len(rows)

    return {"data": rows, "total": total, "limit": limit, "offset": offset}

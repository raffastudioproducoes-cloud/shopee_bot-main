"""
Usuários Router — API Python (FastAPI)

CRUD administrativo de usuários. Só ADMIN acessa (mesma regra do
Flask: web/routes/users.py before_request).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .auth import get_current_user_id
from ..database import supabase

router = APIRouter(prefix="/users", tags=["users"])

NETWORK_TABLES = [
    "shopee_credentials",
    "threads_credentials",
    "x_credentials",
    "facebook_credentials",
    "instagram_credentials",
    "tiktok_credentials",
    "kwai_credentials",
]


class UserCreate(BaseModel):
    username: str
    password: str
    access: str = "USER"


class UserUpdate(BaseModel):
    username: str
    access: str


def _require_admin(user_id: int = Depends(get_current_user_id)) -> int:
    result = (
        supabase.table("users").select("access").eq("id", user_id)
        .single().execute()
    )
    if not result.data or result.data.get("access") != "ADMIN":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user_id


@router.get("")
async def list_users(
    _admin_id: int = Depends(_require_admin),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    query = (
        supabase.table("users")
        .select("id, username, access, created_at, updated_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)
    result = query.execute()

    next_cursor = None
    if result.data and len(result.data) == limit:
        next_cursor = result.data[-1]["created_at"]

    return {"data": result.data, "next_cursor": next_cursor}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, _admin_id: int = Depends(_require_admin)):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    if body.access not in ("USER", "ADMIN"):
        raise HTTPException(status_code=400, detail="access deve ser USER ou ADMIN")

    if body.username.lower() == "rafastudio":
        # Mesmo motivo do register() em auth.py: bloqueia squatting do
        # username reservado da conta master-admin.
        raise HTTPException(status_code=409, detail="Nome de usuário já existe")

    result = (
        supabase.table("users")
        .insert({
            "username": body.username,
            "password": pwd_context.hash(body.password),
            "access": body.access,
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar usuário")

    new_user_id = result.data[0]["id"]

    # Semeia uma linha vazia de credencial por rede — mesmo padrão do
    # Flask (web/routes/users.py) para a tela de credenciais sempre
    # ter uma linha pra cada rede, independente de já ter conectado.
    for table in NETWORK_TABLES:
        supabase.table(table).insert({"user_id": new_user_id, "status": False}).execute()

    return result.data[0]


@router.get("/{user_id}")
async def get_user(user_id: str, _admin_id: int = Depends(_require_admin)):
    result = (
        supabase.table("users")
        .select("id, username, access, created_at, updated_at")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return result.data


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    _admin_id: int = Depends(_require_admin),
):
    if body.access not in ("USER", "ADMIN"):
        raise HTTPException(status_code=400, detail="access deve ser USER ou ADMIN")

    current = (
        supabase.table("users").select("username, access").eq("id", user_id)
        .single().execute()
    )
    if current.data and current.data.get("username", "").lower() == "rafastudio":
        if body.access != "ADMIN":
            raise HTTPException(status_code=403, detail="Esta conta deve permanecer ADMIN")
        if body.username != current.data.get("username"):
            raise HTTPException(status_code=403, detail="Esta conta não pode ser renomeada")

    result = (
        supabase.table("users")
        .update({"username": body.username, "access": body.access})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return result.data[0]


@router.delete("/{user_id}")
async def delete_user(user_id: str, _admin_id: int = Depends(_require_admin)):
    current = (
        supabase.table("users").select("username, access").eq("id", user_id)
        .single().execute()
    )
    if current.data and current.data.get("username", "").lower() == "rafastudio":
        raise HTTPException(status_code=403, detail="Esta conta não pode ser removida")

    result = supabase.table("users").delete().eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"msg": "Usuário removido"}

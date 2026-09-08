"""
Router placeholder — Users (API Python)
CRUD de usuários administrativos.
Baseado em: database/users.py
Próxima atualização: implementar com Supabase real.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])


# --- Schemas ---

class UserCreate(BaseModel):
    username: str
    password: str
    access: str = "ADMIN"


class UserUpdate(BaseModel):
    username: str | None = None
    access: str | None = None


# --- Endpoints ---

@router.get("/")
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Lista de usuários (paginated)."""
    # TODO: implementar com Supabase
    raise HTTPException(status_code=501, detail="Não implementado")


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Detalhes de um usuário."""
    # TODO: implementar com Supabase
    raise HTTPException(status_code=501, detail="Não implementado")


@router.post("/", status_code=201)
async def create_user(user: UserCreate):
    """Cria um usuário."""
    # TODO: implementar com Supabase
    raise HTTPException(status_code=501, detail="Não implementado")


@router.put("/{user_id}")
async def update_user(user_id: str, user: UserUpdate):
    """Atualiza um usuário."""
    # TODO: implementar com Supabase
    raise HTTPException(status_code=501, detail="Não implementado")


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Remove um usuário."""
    # TODO: implementar com Supabase
    raise HTTPException(status_code=501, detail="Não implementado")

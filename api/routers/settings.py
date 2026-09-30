"""
Settings Router — API Python (FastAPI)

Troca de senha self-service para o usuário já autenticado (diferente de
`/auth/reset-password`, que exige só o username + senha atual, sem sessão).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..database import supabase
from .auth import _validate_password_length, get_current_user_id, pwd_context

router = APIRouter(prefix="/settings", tags=["settings"])


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.put("/password")
async def change_password(
    body: PasswordChange, user_id: int = Depends(get_current_user_id)
):
    _validate_password_length(body.new_password)

    result = (
        supabase.table("users")
        .select("id, password")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data or not pwd_context.verify(
        body.current_password, result.data["password"]
    ):
        raise HTTPException(status_code=403, detail="Senha atual incorreta")

    new_hash = pwd_context.hash(body.new_password)
    supabase.table("users").update({"password": new_hash}).eq("id", user_id).execute()
    return {"status": "updated"}

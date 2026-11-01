"""
Settings Router — API Python (FastAPI)

Troca de senha self-service para o usuário já autenticado (diferente de
`/auth/reset-password`, que exige só o username + senha atual, sem sessão).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ..database import supabase
from .auth import (
    _check_login_rate_limit,
    _create_token,
    _decode_token,
    _password_version,
    _validate_password_length,
    get_current_user_id,
    pwd_context,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.put("/password")
async def change_password(
    body: PasswordChange,
    request: Request,
    response: Response,
    user_id: str = Depends(get_current_user_id),
):
    _check_login_rate_limit(f"changepw:{user_id}")
    _validate_password_length(body.new_password)

    result = (
        supabase.table("users")
        .select("id, username, password")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if result.data and result.data.get("supabase_auth_user_id"):
        raise HTTPException(status_code=409, detail="Senha gerenciada pelo Supabase Auth; utilize o fluxo de alteração de senha do provedor.")
    if not result.data or not result.data.get("password") or not pwd_context.verify(
        body.current_password, result.data["password"]
    ):
        raise HTTPException(status_code=403, detail="Senha atual incorreta")

    new_hash = pwd_context.hash(body.new_password)
    supabase.table("users").update({"password": new_hash}).eq("id", user_id).execute()

    # A troca invalida todos os JWTs antigos (claim `pwv`); reemite o cookie
    # só pra sessão atual, pra quem trocou a senha não ser deslogado.
    old_token = request.cookies.get("access_token")
    old_payload = (_decode_token(old_token) if old_token else None) or {}
    response.set_cookie(
        key="access_token",
        value=_create_token({
            "sub": result.data.get("username"),
            "id": user_id,
            "profile_id": old_payload.get("profile_id"),
            "pwv": _password_version(new_hash),
        }),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
    )
    return {"status": "updated"}

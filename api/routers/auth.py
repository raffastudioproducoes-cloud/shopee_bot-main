"""
Auth Router — API Python (FastAPI)
Login, logout e perfil de usuário autenticado.

ATENÇÃO: Esta implementação usa JWT simples em cookie httpOnly.
Em uma próxima fase, este mecanismo de auth deverá ser substituído
por uma solução mais robusta (ex: session management com refresh tokens,
ou integração com autenticação centralizada).

Ver: docs/CHECKLIST_MIGRACAO.md — seção "Auth (futuro)".
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from ..config import settings
from ..database import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_token(data: dict, expires_delta: timedelta | None = None) -> str:
    import jwt

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=1)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.api_secret_key, algorithm="HS256")


def _decode_token(token: str) -> dict | None:
    import jwt

    try:
        payload = jwt.decode(
            token, settings.api_secret_key, algorithms=["HS256"]
        )
        return payload
    except Exception:
        return None


def _get_user_from_supabase(username: str):
    supabase = get_supabase()
    response = supabase.table("users").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = _get_user_from_supabase(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    if not pwd_context.verify(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Senha inválida")

    token = _create_token({"sub": user["username"], "id": user["id"]})

    response = Response()
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
    )
    return {"msg": "Login realizado com sucesso"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"msg": "Logout realizado com sucesso"}


@router.get("/me")
async def me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")

    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token sem usuário")

    user = _get_user_from_supabase(username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário inexistente")

    return {
        "id": user["id"],
        "username": user["username"],
        "access": user.get("access", ""),
    }

"""
Auth Router — API Python (FastAPI)

Login, logout e perfil de usuário autenticado.

ATENÇÃO: Esta implementação usa JWT simples em cookie httpOnly.
Em uma próxima fase, este mecanismo de auth deverá ser substituído
por uma solução mais robusta (ex: session management com refresh tokens,
ou integração com autenticação centralizada).

Ver: docs/CHECKLIST_MIGRACAO.md — seção "Auth (futuro)".
"""

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from ..config import settings
from ..database import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])

_DB_UNAVAILABLE_DETAIL = (
    "Serviço de banco de dados indisponível. Verifique a configuração do servidor."
)

# ponytail: cooldown de reset de senha em memória (dict de módulo). Mitigação
# simples pra app de poucos usuários com 1 único worker uvicorn — não é um
# rate-limiter distribuído e não escala pra múltiplos workers/instâncias.
# Upgrade: slowapi/Redis se a app crescer pra multi-worker.
_RESET_COOLDOWN_SECONDS = 60
_last_reset_attempt: dict[str, float] = {}


class ResetPasswordRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    new_password: str


def get_current_user_id(request: Request) -> int:
    """Dependência que extrai o ID do usuário do cookie access_token."""
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

    return user["id"]


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
    try:
        supabase = get_supabase()
    except RuntimeError:
        raise HTTPException(status_code=503, detail=_DB_UNAVAILABLE_DETAIL)
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


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    """Reset de senha self-service, sem verificação de identidade.

    AVISO DE SEGURANÇA (decisão consciente, não bug): este endpoint não
    confirma que quem está fazendo a requisição é o dono da conta — não há
    confirmação por e-mail/SMS porque o app não tem esse canal configurado.
    Qualquer pessoa que souber um username existente pode resetar a senha
    dele. Isso foi pedido explicitamente (botão de "trocar senha" na tela
    de login, sem fluxo de verificação disponível). Mitigações aplicadas:
    resposta genérica idêntica para usuário existente ou não, tempo de
    resposta equalizado entre os dois branches (hash bcrypt dummy quando o
    usuário não existe) e cooldown por username para dificultar reset em
    loop contra a mesma conta.
    """
    now = time.monotonic()
    last_attempt = _last_reset_attempt.get(payload.username)
    _last_reset_attempt[payload.username] = now
    if last_attempt is not None and (now - last_attempt) < _RESET_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Aguarde antes de tentar novamente.",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ter no mínimo 8 caracteres.",
        )
    if len(payload.new_password) > 72:
        raise HTTPException(
            status_code=400,
            detail="Senha não pode ter mais de 72 caracteres.",
        )

    generic_response = {"msg": "Se o usuário existir, a senha foi atualizada"}

    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = _get_user_from_supabase(payload.username)
    if not user:
        # Hash dummy só pra equalizar o tempo de resposta com o branch que
        # atualiza a senha (evita inferir existência do username via
        # timing) — nada é persistido.
        pwd_context.hash("dummy_password_for_timing")
        return generic_response

    hashed = pwd_context.hash(payload.new_password)

    get_supabase().table("users").update({"password": hashed}).eq(
        "username", payload.username
    ).execute()

    return generic_response

"""
Auth Router — API Python (FastAPI)

Login, logout e perfil de usuário autenticado.

ATENÇÃO: Esta implementação usa JWT simples em cookie httpOnly.
Em uma próxima fase, este mecanismo de auth deverá ser substituído
por uma solução mais robusta (ex: session management com refresh tokens,
ou integração com autenticação centralizada).

Ver: docs/CHECKLIST_MIGRACAO.md — seção "Auth (futuro)".
"""

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from ..config import settings
from ..database import get_supabase, supabase
from .. import rate_limit_store

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Instância única de módulo — reusada por login/reset_password/register aqui
# e por api/routers/settings.py (troca de senha em /settings). Não criar uma
# segunda instância de CryptContext em outro módulo.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DB_UNAVAILABLE_DETAIL = (
    "Serviço de banco de dados indisponível. Verifique a configuração do servidor."
)

# ponytail: cooldown de reset de senha em memória (dict de módulo). Mitigação
# simples pra app de poucos usuários com 1 único worker uvicorn — não é um
# rate-limiter distribuído e não escala pra múltiplos workers/instâncias.
# Upgrade: slowapi/Redis se a app crescer pra multi-worker.
_RESET_COOLDOWN_SECONDS = 60
_last_reset_attempt: dict[str, float] = {}

# Mesmo ponytail acima, agora por IP (cada registro tem username diferente,
# então cooldown por username não protegeria contra spam de contas novas).
_REGISTER_COOLDOWN_SECONDS = 30
_last_register_attempt: dict[str, float] = {}

# ponytail: rate limit de login em memória de processo (dict de módulo,
# chave IP+username, janela deslizante simples via lista de timestamps).
# Mesma limitação dos cooldowns acima: não escala pra múltiplos workers/
# instâncias — cada worker teria seu próprio dict e o limite efetivo vira
# N_tentativas * N_workers. Upgrade: slowapi + Redis se a app crescer.
_LOGIN_RATE_LIMIT_ATTEMPTS = 5
_LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
_login_attempts: dict[str, list[float]] = {}

NETWORK_TABLES = [
    "shopee_credentials",
    "threads_credentials",
    "x_credentials",
    "facebook_credentials",
    "instagram_credentials",
    "tiktok_credentials",
    "kwai_credentials",
]


def provision_new_user(supabase, new_user: dict) -> None:
    """Semeia credenciais vazias por rede + perfil principal da conta nova
    (compartilhado por /auth/register e POST /users do admin).

    O perfil principal é criado primeiro: as credenciais vazias já nascem com
    `profile_id` dele.

    Perfil principal — mesmo padrão do backfill da migração 035. Sem ele, o
    primeiro perfil criado via POST /profiles nasceria "secundario" e a
    conta ficaria sem nenhum perfil protegido contra exclusão.

    Se qualquer insert falhar, desfaz o usuário (FK ON DELETE CASCADE limpa
    o que já foi semeado) pra não deixar conta órfã, e devolve 500 genérico.
    """
    try:
        profile = supabase.table("profiles").insert({
            "user_id": new_user["id"],
            "kind": "principal",
            "nome": new_user["username"],
        }).execute()
        if not profile.data:
            raise RuntimeError("insert de perfil principal sem retorno")
        # Credenciais vazias nascem já ligadas ao perfil principal (multi-perfil).
        for table in NETWORK_TABLES:
            supabase.table(table).insert(
                {"user_id": new_user["id"], "profile_id": profile.data[0]["id"], "status": False}
            ).execute()
    except Exception:
        logger.exception("Falha ao provisionar usuário %s; desfazendo", new_user["id"])
        try:
            supabase.table("users").delete().eq("id", new_user["id"]).execute()
        except Exception:
            logger.exception("Falha ao desfazer usuário órfão %s", new_user["id"])
        raise HTTPException(status_code=500, detail="Falha ao criar usuário")


class ResetPasswordRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    current_password: str
    new_password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str
    accepted_terms_version: str | None = None


def _validate_password_length(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ter no mínimo 8 caracteres.",
        )
    # bcrypt trunca silenciosamente em 72 BYTES (não caracteres): emojis/acentos
    # contam mais de 1 byte, então validamos o tamanho em UTF-8.
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Senha não pode ter mais de 72 bytes (emojis e acentos ocupam mais de 1).",
        )


def _password_version(password_hash: str | None) -> str:
    """Fingerprint curto do hash de senha atual, embutido no JWT (claim
    `pwv`). Trocar a senha muda o hash e, portanto, invalida os tokens
    emitidos antes — sem coluna nova nem migração."""
    return hashlib.sha256((password_hash or "").encode("utf-8")).hexdigest()[:16]


def _get_authenticated_user(token: str) -> dict:
    """Decodifica o token e resolve o usuário — compartilhado por
    `get_current_user_id` e `/auth/me` (evita duplicar a checagem abaixo).

    Rejeita quando o `id` do token não bate com o `id` atual do usuário
    daquele `username`: sem isso, um JWT antigo (emitido antes de uma
    autoexclusão de conta, válido por até 24h) autenticaria como uma
    conta NOVA que reusasse o mesmo username depois do cadastro público
    reabrir aquele nome — o `sub` (username) sozinho não é suficiente
    pra identificar a conta.
    """
    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token sem usuário")

    user = _get_user_from_supabase(username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário inexistente")

    if str(payload.get("id")) != str(user["id"]):
        raise HTTPException(status_code=401, detail="Token inválido")

    session_id = payload.get("jti")
    if not session_id:
        # Tokens emitidos antes desta mudanca exigem um novo login.
        raise HTTPException(status_code=401, detail="Sessão expirada")
    try:
        db = get_supabase()
    except RuntimeError:
        raise HTTPException(status_code=503, detail=_DB_UNAVAILABLE_DETAIL)
    revoked = (
        db.table("revoked_sessions")
        .select("jti").eq("jti", session_id).maybe_single().execute()
    )
    if revoked and isinstance(revoked.data, dict) and revoked.data.get("jti") == session_id:
        raise HTTPException(status_code=401, detail="Sessão expirada")

    # Tokens sem `pwv` (emitidos antes desta checagem existir) seguem
    # válidos até expirar (24h); todo token novo carrega o claim e morre
    # quando a senha muda.
    pwv = payload.get("pwv")
    if pwv is not None and pwv != _password_version(user.get("password")):
        raise HTTPException(status_code=401, detail="Sessão expirada")

    return user


def get_current_user_id(request: Request) -> str:
    """Dependência que extrai o ID do usuário do cookie access_token."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")

    return _get_authenticated_user(token)["id"]


def _create_token(data: dict, expires_delta: timedelta | None = None) -> str:
    import jwt

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=1)
    )
    to_encode.update({"exp": expire, "jti": str(uuid4())})
    return jwt.encode(to_encode, settings.api_secret_key, algorithm="HS256")


def _revoke_session(token: str, user_id: str) -> None:
    payload = _decode_token(token)
    if not payload or not payload.get("jti"):
        return
    supabase.table("revoked_sessions").insert({
        "jti": payload["jti"],
        "user_id": user_id,
        "expires_at": datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat(),
    }).execute()


def cleanup_expired_sessions() -> None:
    supabase.table("revoked_sessions").delete().lt(
        "expires_at", datetime.now(timezone.utc).isoformat()
    ).execute()


def _decode_token(token: str) -> dict | None:
    import jwt

    try:
        decoded = jwt.decode_complete(
            token, settings.api_secret_key, algorithms=["HS256"]
        )
        header = decoded.get("header") or {}
        if "crit" in header:
            # RFC 7515 §4.1.11 / GHSA-752w-5fwx-jx9f: nenhuma extensão crítica é suportada
            return None
        return decoded.get("payload")
    except Exception:
        return None


def _get_user_from_supabase(username: str):
    try:
        supabase = get_supabase()
    except RuntimeError:
        raise HTTPException(status_code=503, detail=_DB_UNAVAILABLE_DETAIL)
    response = supabase.table("users").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None


def _check_login_rate_limit(
    key: str,
    detail: str = "Muitas tentativas de login. Aguarde antes de tentar novamente.",
) -> None:
    if rate_limit_store.distributed_enabled():
        if not rate_limit_store.allow_window(
            "login", key, _LOGIN_RATE_LIMIT_ATTEMPTS, _LOGIN_RATE_LIMIT_WINDOW_SECONDS
        ):
            raise HTTPException(status_code=429, detail=detail)
        return

    now = time.monotonic()
    attempts = [
        t for t in _login_attempts.get(key, [])
        if now - t < _LOGIN_RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(attempts) >= _LOGIN_RATE_LIMIT_ATTEMPTS:
        _login_attempts[key] = attempts
        raise HTTPException(status_code=429, detail=detail)
    attempts.append(now)
    _login_attempts[key] = attempts


# Em produção o FastAPI só recebe tráfego do proxy Flask local
# (web/routes/api_proxy.py -> 127.0.0.1:8001), então `request.client.host`
# é sempre 127.0.0.1 e todo rate limit por IP vira global. O proxy repassa
# o IP real (já resolvido pelo ProxyFix do Flask) em X-Forwarded-For; só
# confiamos nesse header quando a conexão vem do loopback (o próprio proxy).
_TRUSTED_PROXY_HOSTS = {"127.0.0.1", "::1"}


def client_ip(request) -> str:
    host = request.client.host if request.client else "unknown"
    if host in _TRUSTED_PROXY_HOSTS:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[-1].strip()
        if forwarded:
            return forwarded
    return host


_INVALID_LOGIN_DETAIL = "Usuário ou senha inválidos"


@router.post("/login")
async def login(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    # A identidade é estável mesmo quando o proxy alterna o IP de origem entre
    # requisições. Isso impede contornar o limite mudando de conexão.
    _check_login_rate_limit(f"login:{form_data.username.casefold()}")

    user = _get_user_from_supabase(form_data.username)
    if not user:
        # Mesma mensagem e custo de bcrypt do caso "senha errada": não
        # revela quais usernames existem (nem por texto nem por timing).
        pwd_context.hash("dummy_password_for_timing")
        raise HTTPException(status_code=401, detail=_INVALID_LOGIN_DETAIL)

    if not pwd_context.verify(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail=_INVALID_LOGIN_DETAIL)

    principal = (
        get_supabase()
        .table("profiles")
        .select("id")
        .eq("user_id", user["id"])
        .eq("kind", "principal")
        .maybe_single()
        .execute()
    )
    # isinstance (nao só truthiness): testes existentes de login mockam
    # `get_supabase` sem prever esta query nova de perfil principal, e o
    # `.execute()` auto-gerado pelo MagicMock devolve outro MagicMock (que
    # é truthy e nao é dict) -- sem essa checagem, `.data["id"]` levantaria
    # ou o token ficaria com um MagicMock como claim (falha na serializacao
    # JSON do JWT). Resposta real do Supabase pra maybe_single() é sempre
    # `None` ou `dict`.
    profile_id = (
        principal.data["id"] if isinstance(principal.data, dict) else None
    )
    token = _create_token({
        "sub": user["username"],
        "id": user["id"],
        "profile_id": profile_id,
        "pwv": _password_version(user.get("password")),
    })

    # response injetado pelo FastAPI, não um Response() local — um Response()
    # criado à mão é descartado quando a função retorna um dict (bug que
    # fazia o cookie de sessão nunca ser enviado, login "funcionava" mas
    # /me sempre voltava 401 logo em seguida).
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
async def logout(response: Response, request: Request):
    token = request.cookies.get("access_token")
    if token:
        try:
            user = _get_authenticated_user(token)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
        else:
            _revoke_session(token, user["id"])
    response.delete_cookie(key="access_token")
    return {"msg": "Logout realizado com sucesso"}


@router.get("/me")
async def me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")

    user = _get_authenticated_user(token)

    # Mesma regra de get_current_profile_id (import tardio: profiles importa auth).
    from .profiles import _resolve_profile_id

    claim = (_decode_token(token) or {}).get("profile_id")
    return {
        "id": user["id"],
        "username": user["username"],
        "access": user.get("access", ""),
        "profile_id": _resolve_profile_id(claim, user["id"]),
    }


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    """Troca de senha self-service, exigindo prova de posse da conta.

    Este endpoint NÃO é um fluxo de "esqueci minha senha" de verdade — o
    app não tem canal de e-mail/SMS configurado (ver requirements.txt),
    então não há como confirmar identidade de quem não sabe a senha atual.
    Por isso exige `current_password`: serve pra troca de senha de quem
    ainda tem a senha antiga em mãos, não pra recuperação de conta perdida
    (esse caso exige intervenção manual de admin no banco). Mitigações
    mantidas: resposta genérica idêntica pra usuário inexistente/senha
    errada/sucesso, tempo de resposta equalizado (hash bcrypt dummy quando
    o usuário não existe) e cooldown por username.
    """
    if rate_limit_store.distributed_enabled():
        if not rate_limit_store.acquire_cooldown(
            "reset", payload.username.casefold(), _RESET_COOLDOWN_SECONDS
        ):
            raise HTTPException(
                status_code=429, detail="Aguarde antes de tentar novamente."
            )
    else:
        now = time.monotonic()
        last_attempt = _last_reset_attempt.get(payload.username)
        _last_reset_attempt[payload.username] = now
        if last_attempt is not None and (now - last_attempt) < _RESET_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail="Aguarde antes de tentar novamente.",
            )

    _validate_password_length(payload.new_password)

    generic_response = {"msg": "Se o usuário existir, a senha foi atualizada"}

    user = _get_user_from_supabase(payload.username)
    if not user:
        # Hash dummy só pra equalizar o tempo de resposta com o branch que
        # atualiza a senha (evita inferir existência do username via
        # timing) — nada é persistido.
        pwd_context.hash("dummy_password_for_timing")
        return generic_response

    if not pwd_context.verify(payload.current_password, user.get("password", "")):
        # Mesma resposta genérica de "usuário não existe" — não revela se
        # foi o username ou a senha atual que estava errada.
        return generic_response

    hashed = pwd_context.hash(payload.new_password)

    get_supabase().table("users").update({"password": hashed}).eq(
        "username", payload.username
    ).execute()

    return generic_response


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, request: Request):
    """Cadastro público. Sempre cria com access="USER" — o cliente não tem
    como enviar ADMIN, o campo nem existe no schema de entrada."""
    ip = client_ip(request)
    if rate_limit_store.distributed_enabled():
        if not rate_limit_store.acquire_cooldown(
            "register", ip, _REGISTER_COOLDOWN_SECONDS
        ):
            raise HTTPException(
                status_code=429, detail="Aguarde antes de tentar novamente."
            )
    else:
        now = time.monotonic()
        last_attempt = _last_register_attempt.get(ip)
        _last_register_attempt[ip] = now
        if last_attempt is not None and (now - last_attempt) < _REGISTER_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail="Aguarde antes de tentar novamente.",
            )

    _validate_password_length(body.password)
    if body.accepted_terms_version != "2026-10-31":
        raise HTTPException(status_code=422, detail="Leia e aceite os Termos de Uso vigentes para criar uma conta.")

    if body.username.lower() == "rafastudio":
        # Nome reservado da conta master-admin — bloqueia squatting via
        # cadastro público (ex: "RafaStudio", "RAFASTUDIO"). Checagem
        # pontual só pra esse username, não unicidade case-insensitive geral.
        raise HTTPException(status_code=409, detail="Nome de usuário já existe")

    if _get_user_from_supabase(body.username):
        raise HTTPException(status_code=409, detail="Nome de usuário já existe")

    try:
        supabase = get_supabase()
    except RuntimeError:
        raise HTTPException(status_code=503, detail=_DB_UNAVAILABLE_DETAIL)

    result = (
        supabase.table("users")
        .insert({
            "username": body.username,
            "password": pwd_context.hash(body.password),
            "access": "USER",
            "legal_terms_version": "2026-10-31",
            "legal_terms_accepted_at": datetime.now(timezone.utc).isoformat(),
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar usuário")

    new_user = result.data[0]

    provision_new_user(supabase, new_user)

    return {
        "id": new_user["id"],
        "username": new_user["username"],
        "access": "USER",
    }

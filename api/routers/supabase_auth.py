"""Entrada no Supabase Auth (e-mail + Google) durante a migração do Auto Orbital.

Os IDs de public.users continuam a ser o identificador comercial da conta.
Nenhuma identidade nova é associada a contas legadas por e-mail ou nome.
As sessões internas JWT são ponte temporária e serão retiradas no cutover final.
"""
import base64
import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from supabase import create_client

from ..config import settings
from ..database import get_supabase
from .auth import (
    _check_login_rate_limit, _create_token, _validate_password_length,
    client_ip, provision_new_user,
)

router = APIRouter(prefix="/auth/supabase", tags=["auth"])
logger = logging.getLogger(__name__)
TERMS_VERSION = "2026-10-31"
COOKIE_OPTS = dict(httponly=True, secure=True, samesite="lax", path="/")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_USERNAME_RE = re.compile(r"^[\w.-]{3,64}$", re.UNICODE)


def _require_config(google=False):
    if not settings.supabase_auth_enabled or not settings.supabase_auth_publishable_key:
        raise HTTPException(503, "Autenticação Supabase ainda não configurada.")
    if google and not settings.supabase_auth_redirect_base_url:
        raise HTTPException(503, "URL pública do callback Google não configurada.")


def _auth_client():
    _require_config()
    # Cliente por chamada: nunca compartilhar estado de sessão entre usuários.
    return create_client(settings.supabase_url, settings.supabase_auth_publishable_key)


def _normalized_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not _EMAIL_RE.fullmatch(email):
        raise HTTPException(422, "Informe um e-mail válido.")
    return email


def _validate_username(username: str):
    if not _USERNAME_RE.fullmatch(username) or username.casefold() == "rafastudio":
        raise HTTPException(422, "Nome de usuário inválido ou reservado.")


def _local_user(auth_id: str):
    result = (get_supabase().table("users").select("*")
              .eq("supabase_auth_user_id", auth_id).maybe_single().execute())
    return result.data if result else None


def _issue_session(response: Response, user: dict):
    profile = (get_supabase().table("profiles").select("id")
               .eq("user_id", user["id"]).eq("kind", "principal")
               .maybe_single().execute())
    profile_id = profile.data["id"] if profile and profile.data else None
    # Compatibilidade transitória com dependências de perfis e jobs da API.
    # A senha nunca é verificada nem armazenada aqui para identidades Supabase.
    token = _create_token({
        "sub": user["username"], "id": user["id"],
        "profile_id": profile_id, "pwv": hashlib.sha256(
            (user.get("password") or "").encode("utf-8")
        ).hexdigest()[:16],
        "auth_source": "supabase",
    })
    response.set_cookie("access_token", token, max_age=86400, **COOKIE_OPTS)


def _create_local_account(username: str, email: str, auth_id: str) -> dict:
    _validate_username(username)
    db = get_supabase()
    if _local_user(auth_id):
        raise HTTPException(409, "Identidade já associada a uma conta.")
    # Email não substitui a prova de propriedade da conta antiga.
    duplicate = (db.table("users").select("id").ilike("email", email)
                 .limit(1).execute())
    if duplicate.data:
        raise HTTPException(409, "E-mail já associado a outra conta.")
    existing = db.table("users").select("id").eq("username", username).limit(1).execute()
    if existing.data:
        raise HTTPException(409, "Nome de usuário já existe.")
    now = datetime.now(timezone.utc).isoformat()
    result = db.table("users").insert({
        "username": username, "email": email, "password": None, "access": "USER",
        "supabase_auth_user_id": auth_id,
        "legal_terms_version": TERMS_VERSION, "legal_terms_accepted_at": now,
    }).execute()
    if not result.data:
        raise HTTPException(503, "Não foi possível concluir o cadastro.")
    user = result.data[0]
    provision_new_user(db, user)
    return user


class EmailRegistration(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=5, max_length=254)
    password: str
    confirm_password: str
    accepted_terms_version: str


class EmailLogin(BaseModel):
    email: str
    password: str


class CompleteGoogle(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    accepted_terms_version: str


@router.get("/config")
async def configuration():
    enabled = bool(settings.supabase_auth_enabled and settings.supabase_auth_publishable_key)
    return {"email_enabled": enabled,
            "google_enabled": enabled and bool(settings.supabase_auth_redirect_base_url)}


@router.post("/register", status_code=201)
async def register_email(body: EmailRegistration, request: Request):
    _require_config()
    _check_login_rate_limit(f"supabase-register:{client_ip(request)}")
    if body.accepted_terms_version != TERMS_VERSION:
        raise HTTPException(422, "Aceite os Termos de Uso vigentes.")
    _validate_username(body.username)
    _validate_password_length(body.password)
    if body.password != body.confirm_password:
        raise HTTPException(422, "As senhas não coincidem.")
    email = _normalized_email(body.email)
    try:
        result = _auth_client().auth.sign_up({
            "email": email, "password": body.password,
        })
    except Exception:
        logger.warning("Supabase Auth recusou cadastro", exc_info=False)
        raise HTTPException(400, "Não foi possível criar a conta com esse e-mail.") from None
    if not result.user or not result.session:
        # Não provisionar sem sessão válida. Desative a confirmação de e-mail
        # no painel Supabase conforme decisão explícita do proprietário.
        raise HTTPException(409, "Cadastro pendente no Supabase. Verifique a configuração de confirmação de e-mail.")
    user = _create_local_account(body.username, email, str(result.user.id))
    return {"id": user["id"], "username": user["username"], "access": "USER"}


@router.post("/login")
async def login_email(body: EmailLogin, request: Request, response: Response):
    _require_config()
    email = _normalized_email(body.email)
    _check_login_rate_limit(f"supabase-login:{email}")
    try:
        result = _auth_client().auth.sign_in_with_password({
            "email": email, "password": body.password,
        })
    except Exception:
        raise HTTPException(401, "E-mail ou senha inválidos.") from None
    if not result.user or not result.session:
        raise HTTPException(401, "E-mail ou senha inválidos.")
    user = _local_user(str(result.user.id))
    if not user:
        raise HTTPException(403, "Identidade ainda não associada a uma conta do Auto Orbital.")
    _issue_session(response, user)
    return {"msg": "Login realizado com Supabase Auth"}


def _verify_google_token(token: str):
    try:
        result = _auth_client().auth.get_user(token)
    except Exception:
        raise HTTPException(401, "Autorização Google expirada ou inválida.") from None
    user = result.user
    if not user or not user.id or not user.email:
        raise HTTPException(401, "Identidade Google inválida.")
    # Escopos de perfil/e-mail, não permissão administrativa.
    return user


@router.get("/google/authorize")
async def google_authorize():
    _require_config(google=True)
    origin = settings.supabase_auth_redirect_base_url.rstrip("/")
    if not origin.startswith("https://") and not origin.startswith("http://localhost:"):
        raise HTTPException(503, "Origem OAuth deve utilizar HTTPS.")
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    callback = f"{origin}/api/auth/supabase/google/callback"
    auth_url = settings.supabase_url.rstrip("/") + "/auth/v1/authorize?" + urlencode({
        "provider": "google", "redirect_to": callback,
        "code_challenge": challenge, "code_challenge_method": "s256",
    })
    state = jwt.encode({
        "verifier": verifier, "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "purpose": "supabase-google-pkce",
    }, settings.api_secret_key, algorithm="HS256")
    response = RedirectResponse(auth_url, status_code=302)
    response.set_cookie("sb_google_pkce", state, max_age=300, **COOKIE_OPTS)
    return response


@router.get("/google/callback")
async def google_callback(request: Request):
    _require_config(google=True)
    response_fail = RedirectResponse("/login?google_error=1", status_code=303)
    code = request.query_params.get("code")
    cookie = request.cookies.get("sb_google_pkce")
    if not code or not cookie or request.query_params.get("error"):
        return response_fail
    try:
        state = jwt.decode(cookie, settings.api_secret_key, algorithms=["HS256"])
        if state.get("purpose") != "supabase-google-pkce":
            return response_fail
        token_url = settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=pkce"
        with httpx.Client(timeout=10) as http:
            res = http.post(token_url,
                headers={"apikey": settings.supabase_auth_publishable_key},
                json={"auth_code": code, "code_verifier": state["verifier"]})
            res.raise_for_status()
            access_token = res.json()["access_token"]
        google_user = _verify_google_token(access_token)
    except Exception:
        logger.warning("Callback Google rejeitado", exc_info=False)
        return response_fail
    existing = _local_user(str(google_user.id))
    if existing:
        dest = RedirectResponse("/", status_code=303)
        _issue_session(dest, existing)
    else:
        # Cadastro novo só após aceite explícito dos termos e escolha do usuário.
        pending = jwt.encode({
            "sub": str(google_user.id), "supabase_token": access_token,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "purpose": "google-pending",
        }, settings.api_secret_key, algorithm="HS256")
        dest = RedirectResponse("/login?google_setup=1", status_code=303)
        dest.set_cookie("sb_google_pending", pending, max_age=600, **COOKIE_OPTS)
    dest.delete_cookie("sb_google_pkce", path="/")
    return dest


@router.post("/google/complete", status_code=201)
async def google_complete(body: CompleteGoogle, request: Request, response: Response):
    _require_config(google=True)
    _check_login_rate_limit(f"google-complete:{client_ip(request)}")
    if body.accepted_terms_version != TERMS_VERSION:
        raise HTTPException(422, "Aceite os Termos de Uso vigentes.")
    pending = request.cookies.get("sb_google_pending")
    if not pending:
        raise HTTPException(401, "Inicie novamente o cadastro com Google.")
    try:
        payload = jwt.decode(pending, settings.api_secret_key, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Cadastro Google expirado.") from None
    if payload.get("purpose") != "google-pending":
        raise HTTPException(401, "Cadastro Google inválido.")
    google_user = _verify_google_token(payload["supabase_token"])
    if str(google_user.id) != payload["sub"]:
        raise HTTPException(401, "Identidade inválida.")
    user = _create_local_account(body.username, _normalized_email(google_user.email), str(google_user.id))
    _issue_session(response, user)
    response.delete_cookie("sb_google_pending", path="/")
    return {"id": user["id"], "username": user["username"], "access": "USER"}

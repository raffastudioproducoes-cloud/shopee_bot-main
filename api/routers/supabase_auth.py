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
from types import SimpleNamespace
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
    if user.get("account_deletion_started_at"):
        raise HTTPException(403, "Esta conta está em processo de exclusão.")
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


class PasswordRecoveryRequest(BaseModel):
    email: str


class PasswordRecoveryComplete(BaseModel):
    access_token: str = Field(min_length=20, max_length=16384)
    new_password: str
    confirm_password: str


class CompleteGoogle(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    accepted_terms_version: str


@router.get("/config")
async def configuration():
    enabled = bool(
        settings.supabase_auth_enabled
        and settings.supabase_auth_publishable_key
        and settings.supabase_auth_redirect_base_url
    )
    return {
        "email_enabled": enabled,
        "email_signup_enabled": enabled and settings.supabase_auth_email_signup_enabled,
        "google_enabled": enabled,
        "legacy_support_enabled": enabled and bool(settings.supabase_legacy_support_username.strip()),
    }


@router.post("/register", status_code=202)
async def register_email(body: EmailRegistration, request: Request, response: Response):
    _require_config()
    if not settings.supabase_auth_email_signup_enabled:
        raise HTTPException(403, "Cadastro por e-mail indisponível.")
    if not settings.supabase_auth_redirect_base_url:
        raise HTTPException(503, "Redirecionamento de confirmação não configurado.")
    _check_login_rate_limit(f"supabase-register:{client_ip(request)}")
    if body.accepted_terms_version != TERMS_VERSION:
        raise HTTPException(422, "Aceite os Termos de Uso vigentes.")
    _validate_username(body.username)
    _validate_password_length(body.password)
    if body.password != body.confirm_password:
        raise HTTPException(422, "As senhas não coincidem.")

    email = _normalized_email(body.email)
    db = get_supabase()
    if db.table("users").select("id").eq("username", body.username).limit(1).execute().data:
        raise HTTPException(409, "Nome de usuário já existe.")

    # A verificação pertence ao Supabase Auth; a aplicação não aprova o
    # cadastro por conta própria nem cria um usuário comercial antes da confirmação.
    redirect_url = settings.supabase_auth_redirect_base_url.rstrip("/") + "/login"
    try:
        result = _auth_client().auth.sign_up({
            "email": email,
            "password": body.password,
            "options": {"email_redirect_to": redirect_url},
        })
    except Exception:
        logger.warning("Falha no início do cadastro com confirmação", exc_info=False)
        raise HTTPException(503, "Não foi possível enviar a confirmação agora.") from None

    if result.session:
        # Falha segura se alguém desligar Confirm Email por engano.
        raise HTTPException(503, "Confirmação de e-mail obrigatória no Supabase Auth.")
    if result.user:
        try:
            db.table("pending_auth_registrations").insert({
                "auth_user_id": str(result.user.id),
                "email": email,
                "username": body.username,
                "legal_terms_version": TERMS_VERSION,
                "legal_terms_accepted_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            # GoTrue pode retornar usuário ofuscado quando o e-mail já existe.
            # Não revelar existência de conta; login posterior é validado
            # exclusivamente pelo Auth e pelo vínculo pendente.
            logger.warning("Solicitação de cadastro sem registro pendente", exc_info=False)
    return {
        "msg": "Se este e-mail puder ser cadastrado, você receberá uma mensagem para confirmar sua conta.",
        "email_confirmation_required": True,
    }


@router.post("/login")
async def login_email(body: EmailLogin, request: Request, response: Response):
    _require_config()
    email = _normalized_email(body.email)
    _check_login_rate_limit(f"supabase-login:{email}")
    try:
        result = _auth_client().auth.sign_in_with_password({
            "email": email, "password": body.password,
        })
    except Exception as exc:
        if getattr(exc, "code", None) == "email_not_confirmed":
            raise HTTPException(403, "Confirme seu e-mail antes de entrar.") from None
        raise HTTPException(401, "E-mail ou senha inválidos.") from None
    if not result.user or not result.session:
        raise HTTPException(401, "E-mail ou senha inválidos.")
    if not getattr(result.user, "email_confirmed_at", None):
        raise HTTPException(403, "Confirme seu e-mail antes de entrar.")

    auth_id = str(result.user.id)
    user = _local_user(auth_id)
    if not user:
        db = get_supabase()
        row = (db.table("pending_auth_registrations")
               .select("auth_user_id,email,username,legal_terms_version")
               .eq("auth_user_id", auth_id).maybe_single().execute())
        pending = row.data if row else None
        if not pending or _normalized_email(pending["email"]) != email or pending["legal_terms_version"] != TERMS_VERSION:
            raise HTTPException(403, "Cadastro ainda não concluído. Contate o suporte.")
        user = _create_local_account(pending["username"], email, auth_id)
        db.table("pending_auth_registrations").delete().eq("auth_user_id", auth_id).execute()

    _issue_session(response, user)
    return {"msg": "Login realizado com Supabase Auth"}


@router.post("/password/recovery", status_code=202)
async def request_password_recovery(body: PasswordRecoveryRequest, request: Request):
    """Somente GoTrue envia o e-mail; a aplicação não gera links nem altera senhas locais."""
    _require_config()
    if not settings.supabase_auth_redirect_base_url:
        raise HTTPException(503, "Redirecionamento de recuperação não configurado.")
    email = _normalized_email(body.email)
    limit_msg = "Muitas solicitações de recuperação. Aguarde antes de tentar novamente."
    _check_login_rate_limit(f"supabase-recovery-email:{email}", detail=limit_msg)
    _check_login_rate_limit(f"supabase-recovery-ip:{client_ip(request)}", detail=limit_msg)
    redirect_url = settings.supabase_auth_redirect_base_url.rstrip("/") + "/login"
    try:
        _auth_client().auth.reset_password_for_email(
            email, {"redirect_to": redirect_url},
        )
    except Exception:
        logger.warning("Falha ao solicitar recuperação de senha no Supabase Auth", exc_info=False)
        raise HTTPException(503, "Não foi possível enviar o e-mail de recuperação agora.") from None
    # Resposta igual para endereço existente ou inexistente (sem enumeração).
    return {"msg": "Se existir uma conta para este e-mail, enviaremos um link para redefinir a senha."}


@router.post("/password/complete")
async def complete_password_recovery(body: PasswordRecoveryComplete, request: Request):
    """Senha atualizada exclusivamente pelo Supabase Auth após autenticar o link de recuperação.

    O token do link chega ao navegador no fragmento e é removido da URL no mount.
    Somente o token de acesso é enviado; nenhum refresh token ou segredo de serviço.
    """
    _require_config()
    _check_login_rate_limit(
        f"supabase-recovery-complete:{client_ip(request)}",
        detail="Muitas tentativas. Aguarde antes de tentar novamente.",
    )
    _validate_password_length(body.new_password)
    if body.new_password != body.confirm_password:
        raise HTTPException(422, "As senhas não coincidem.")

    try:
        verified = _auth_client().auth.get_user(body.access_token)
    except Exception:
        raise HTTPException(401, "Link de recuperação inválido ou expirado. Solicite outro.") from None
    if not verified.user or not verified.user.id or not getattr(verified.user, "email_confirmed_at", None):
        raise HTTPException(401, "Link de recuperação inválido ou expirado. Solicite outro.")

    try:
        # GoTrue /user aplica a nova senha na identidade Supabase. Nunca alterar
        # public.users.password, que é apenas legado/compatibilidade.
        with httpx.Client(timeout=10) as http:
            result = http.put(
                settings.supabase_url.rstrip("/") + "/auth/v1/user",
                headers={
                    "apikey": settings.supabase_auth_publishable_key,
                    "Authorization": f"Bearer {body.access_token}",
                },
                json={"password": body.new_password},
            )
        if result.status_code in (401, 403):
            raise HTTPException(401, "Link de recuperação inválido ou expirado. Solicite outro.")
        result.raise_for_status()
    except HTTPException:
        raise
    except httpx.HTTPError:
        logger.warning("Falha ao atualizar senha no Supabase Auth", exc_info=False)
        raise HTTPException(503, "Não foi possível redefinir a senha agora.") from None
    return {"msg": "Senha redefinida no Supabase. Entre novamente com sua nova senha."}


def _verify_google_token(token: str):
    """Valida no GoTrue o token retornado pelo OAuth, sem depender de sessão do SDK.

    O cliente supabase-py legado pode falhar localmente com a chave publicável
    moderna (sb_publishable_...), mesmo após /token ter retornado HTTP 200.
    A chamada explícita /auth/v1/user valida a sessão no servidor Supabase.
    Nunca registrar token, corpo da resposta ou e-mail do usuário.
    """
    try:
        with httpx.Client(timeout=10) as http:
            response = http.get(
                settings.supabase_url.rstrip("/") + "/auth/v1/user",
                headers={
                    "apikey": settings.supabase_auth_publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
        response.raise_for_status()
        user = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Validação Google recusada pelo Supabase (HTTP %s)",
                       exc.response.status_code)
        raise HTTPException(401, "Autorização Google expirada ou inválida.") from None
    except (httpx.RequestError, ValueError, TypeError) as exc:
        logger.warning("Falha na validação Google (%s)", type(exc).__name__)
        raise HTTPException(401, "Autorização Google expirada ou inválida.") from None
    if not isinstance(user, dict) or not user.get("id") or not user.get("email"):
        raise HTTPException(401, "Identidade Google inválida.")
    # Escopos de perfil/e-mail, não permissão administrativa.
    return SimpleNamespace(id=str(user["id"]), email=str(user["email"]))


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
    if existing and existing.get("account_deletion_started_at"):
        dest = RedirectResponse("/login?account_unavailable=1", status_code=303)
    elif existing:
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

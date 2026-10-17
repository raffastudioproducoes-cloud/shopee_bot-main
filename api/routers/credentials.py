"""
Credenciais Router — API Python (FastAPI)

CRUD das credenciais de rede social/afiliado. Nunca retorna o valor
cifrado de volta ao cliente — só status (conectado/desconectado).

Shopee valida a credencial ao vivo contra a API deles antes de salvar
(igual o Flask sempre fez) — via web/routes/internal.py, porque
apis/shopee.py depende do alias de pacote shopee_bot.* que só existe
no processo Flask. Se a chamada interna falhar (Flask fora do ar, ou
FLASK_INTERNAL_URL/INTERNAL_API_SECRET não configurados), o save de
Shopee falha com 502 em vez de salvar sem validar — melhor recusar do
que gravar uma credencial nunca verificada.
"""

import asyncio
import logging
import secrets
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from .auth import get_current_user_id
from .profiles import get_current_profile_id
from ..profiles import scope_account, scope_owner
from ..audit_log import log_action
from .. import threads_oauth
from .. import instagram_oauth
from .. import facebook_oauth
from .. import tiktok_oauth
from .. import x_oauth
from ..config import settings
from ..database import supabase
from ..crypto import encrypt, decrypt
from apis import llm as ai_llm
from ..utils.log_sanitizer import sanitize_log_data
from ..internal_client import (
    validate_shopee_credential,
    validate_network_credential,
    InternalApiError,
)

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/credentials", tags=["credentials"])

# Redes onde o usuário final ainda cola App ID/Secret manual (formulário):
# Shopee (é a conta de afiliado do PRÓPRIO usuário, não um "app" — não dá
# pra virar app único sem trocar de dono a comissão) e Kwai (sem API
# pública). X/TikTok/Instagram/Facebook SAÍRAM daqui — app único da
# plataforma (env vars), usuário só clica "Conectar" (ver api/x_oauth.py,
# api/tiktok_oauth.py, api/instagram_oauth.py, api/facebook_oauth.py e
# vault Projetos/ShopeeAutoVendas/27-Migracao-App-Unico-OAuth.md).
SIMPLE_NETWORKS = {
    "shopee": "shopee_credentials",
    "kwai": "kwai_credentials",
}

# Redes com OAuth de app único: tabela + coluna que guarda o token do
# usuário (usada tanto por list_credentials quanto por _test_payload pra
# decidir "conectado" e montar o payload de teste).
OAUTH_NETWORKS = {
    "threads": ("threads_credentials", "access_token"),
    "x": ("x_credentials", "user_access_token"),
    "tiktok": ("tiktok_credentials", "user_access_token"),
    "instagram": ("instagram_credentials", "user_access_token"),
    "facebook": ("facebook_credentials", "page_access_token"),
}


class SimpleCredentialBody(BaseModel):
    app_id: str
    secret: str


class ThreadsCredentialBody(BaseModel):
    t_user_id: str
    access_token: str


# Overrides manuais admin-only (colar token direto, bypassando OAuth — ver
# _require_admin e as rotas PUT /{network}/manual mais abaixo). Só os campos
# que são coluna de verdade em cada tabela (ver migrations 018-030):
# x/tiktok/instagram têm user_access_token, facebook tem page_access_token.
class XManualCredentialBody(BaseModel):
    user_access_token: str
    user_refresh_token: str | None = None
    scope: str | None = None


class FacebookManualCredentialBody(BaseModel):
    page_id: str
    page_access_token: str
    page_name: str | None = None


class TikTokManualCredentialBody(BaseModel):
    open_id: str
    user_access_token: str
    refresh_token: str | None = None


class InstagramManualCredentialBody(BaseModel):
    ig_user_id: str
    user_access_token: str


def _simple_table(network: str) -> str:
    table = SIMPLE_NETWORKS.get(network)
    if not table:
        raise HTTPException(status_code=404, detail=f"Rede '{network}' não suportada")
    return table


# Teste com mais de uma semana não garante mais nada (token revogado, app
# alterado): a luz volta pra amarelo pedindo novo teste.
CHECK_STALE_AFTER = timedelta(days=7)

# Teste automático pós-salvar: o limite do teste (AUTOTEST_TIMEOUT_SECONDS) é
# menor que TESTING_MAX_AGE, que por sua vez é a garantia de que a UI nunca
# fica presa em "Testando…" (ex: processo reiniciado no meio do teste).
AUTOTEST_TIMEOUT_SECONDS = 20
TESTING_MAX_AGE = timedelta(seconds=45)

# Redes com expiração de token gravada: (coluna de expiração, coluna de
# refresh). Token vencido SEM refresh = precisa reconectar; com refresh o
# bot renova sozinho na próxima publicação (scheduler/bot_post_x.py).
_TOKEN_EXPIRY_FIELDS = {"x": ("token_expires_at", "user_refresh_token")}
# Colunas extras lidas só pro status (nunca devolvidas em bruto).
_STATUS_EXTRA_COLUMNS = {"x": ("scope",)}


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        ts = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _token_expired(network: str, row: dict | None) -> bool:
    fields = _TOKEN_EXPIRY_FIELDS.get(network)
    if not fields or not row:
        return False
    expires_at = _parse_ts(row.get(fields[0]))
    return bool(expires_at and expires_at <= datetime.now(timezone.utc) and not row.get(fields[1]))


def _short_reason(message: str | None) -> str:
    text = sanitize_log_data(message or "").strip()
    return (text[:117] + "...") if len(text) > 120 else (text or "falha no teste")


def _connection_state(connected: bool, check: dict | None, token_expired: bool = False) -> tuple[str, str, str]:
    """(light, state, status_text) — uma fonte só pra luz E selo, pra nunca
    mostrar "Conectado" verde com bolinha vermelha sem explicação.

    red: sem credencial, ou salva e nunca testada. yellow: token expirado,
    teste com erro ou teste antigo (> CHECK_STALE_AFTER). green: teste OK
    recente. O teste (POST /{network}/test) é a única fonte de 'ok'/'error'
    e é zerado sempre que a credencial é salva/reconectada."""
    if not connected:
        return "red", "disconnected", "Desconectado"
    if token_expired:
        return "yellow", "expired", "Token expirado — reconecte"
    if check and check.get("state") == "testing":
        started = _parse_ts(check.get("checked_at"))
        if started and datetime.now(timezone.utc) - started <= TESTING_MAX_AGE:
            return "yellow", "testing", "Testando…"
        return "yellow", "error", "Erro: o teste não terminou — clique em Testar conexão"
    if not check:
        return "red", "untested", "Salva, nunca testada — clique em Testar conexão"
    if check.get("state") != "ok":
        return "yellow", "error", f"Erro: {_short_reason(check.get('message'))}"
    checked_at = _parse_ts(check.get("checked_at"))
    if checked_at and datetime.now(timezone.utc) - checked_at > CHECK_STALE_AFTER:
        return "yellow", "stale", "Testada há mais de 7 dias — teste de novo"
    return "green", "ok", "Funcionando"


def _light_for(connected: bool, check: dict | None) -> str:
    return _connection_state(connected, check)[0]


def _status_only(
    row: dict | None, check: dict | None = None, *, token_field: str | None = None, network: str | None = None,
) -> dict:
    """`token_field`: pra redes onde `status` é setado por PUT /credentials/{network}
    (só salva app_id/secret do app — TikTok Client Key/Secret, Instagram App ID/
    Secret) mas a conexão real só existe depois do OAuth (authorize/callback).
    Usar `status` nesses casos reporta "Conectado" com o app_id salvo e nenhum
    token de verdade — bug encontrado em produção (tiktok/instagram com status=True
    e user_access_token NULO). Quando informado, `connected` reflete a presença do
    token OAuth em vez do campo `status`."""
    if token_field:
        connected = bool(row.get(token_field)) if row else False
    else:
        connected = bool(row.get("status")) if row else False
    light, state, status_text = _connection_state(
        connected, check, _token_expired(network, row) if network else False,
    )
    status = {
        "connected": connected,
        "light": light,
        "state": state,
        "status_text": status_text,
        "checked_at": check.get("checked_at") if check else None,
    }
    if network == "x":
        # Campos opcionais (contrato antigo intacto): sem media.write o
        # frontend avisa "reconecte o X" antes do primeiro upload.
        has_media = connected and x_oauth.has_media_write((row or {}).get("scope"))
        status["supports_media"] = has_media
        status["missing_scopes"] = [] if (has_media or not connected) else [x_oauth.MEDIA_SCOPE]
    return status


# tabela de credencial -> rede (pra zerar o teste ao salvar/reconectar)
_TABLE_TO_NETWORK = {
    **{t: n for n, t in SIMPLE_NETWORKS.items()},
    **{t: n for n, (t, _) in OAUTH_NETWORKS.items()},
}


def _is_account_network(network: str) -> bool:
    return network == "shopee" or network.startswith("ai_")


def _scope_check(query, user_id: int, profile_id: str | None, network: str):
    return scope_account(query, user_id) if _is_account_network(network) else scope_owner(query, user_id, profile_id)


def _latest_check(checks: list[dict]) -> dict | None:
    def sort_key(check: dict) -> tuple[str, int]:
        try:
            check_id = int(check.get("id"))
        except (TypeError, ValueError):
            check_id = -1
        return str(check.get("checked_at") or ""), check_id

    return max(
        checks,
        key=sort_key,
        default=None,
    )


def _account_checks(user_id: int) -> dict[str, dict]:
    rows = scope_account(
        supabase.table("credential_checks").select("id, network, state, message, checked_at"), user_id,
    ).execute().data or []
    checks: dict[str, dict] = {}
    for row in rows:
        network = row.get("network")
        if not isinstance(network, str) or not _is_account_network(network):
            continue
        latest = _latest_check([checks[network], row]) if network in checks else row
        checks[network] = latest
    return checks


def _reset_credential_check(table: str, user_id: int, profile_id: str | None) -> None:
    """Credencial nova/reconectada invalida o teste anterior (senão a luz
    verde de um token antigo continuava valendo pro novo)."""
    network = _TABLE_TO_NETWORK.get(table)
    if not network:
        return
    _scope_check(
        supabase.table("credential_checks").delete(), user_id, profile_id, network,
    ).eq("network", network).execute()


def _upsert_by_user(table: str, user_id: int, data: dict, profile_id: str | None = None) -> dict:
    """update-or-insert por user_id (e por perfil ativo, quando houver). Não
    existe unique constraint em user_id nessas tabelas (só em app_id/
    t_user_id) — upsert nativo do Postgres via on_conflict não se aplica
    aqui. A Shopee é compartilhada pela conta; as demais continuam por
    perfil ativo e o insert grava `profile_id`."""
    account_scoped = table == "shopee_credentials"
    scope = scope_account if account_scoped else scope_owner
    existing = (
        scope(supabase.table(table).select("id"), user_id) if account_scoped
        else scope(supabase.table(table).select("id"), user_id, profile_id)
    )
    existing = existing.maybe_single().execute()
    if existing and existing.data:
        query = scope(supabase.table(table).update(data), user_id) if account_scoped else scope(
            supabase.table(table).update(data), user_id, profile_id,
        )
        result = query.execute()
    else:
        row = {**data, "user_id": user_id}
        if profile_id and not account_scoped:
            row["profile_id"] = profile_id
        result = supabase.table(table).insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar credencial")
    _reset_credential_check(table, user_id, profile_id)
    network = _TABLE_TO_NETWORK.get(table)
    if network:
        _start_autotest(network, user_id, profile_id)
    return result.data[0]


# Account-linking CSRF (Threads, Instagram, TikTok, X): não existe
# mecanismo de estado efêmero (sessão de servidor) no resto da API —
# cookie httponly assinado (JWT, mesma chave/lib do access_token de
# auth.py) guardando o `state` (e, no caso do X, o code_verifier PKCE)
# entre /authorize e /callback, 10 min de validade. Sem isso, um
# atacante pode iniciar o próprio OAuth, pegar o `code` gerado pra
# conta dele, e induzir a vítima logada a abrir esse link no
# /callback — linkando a conta social do atacante ao usuário da
# vítima. O `state` amarra o /callback ao /authorize que a MESMA
# sessão (cookie httponly) iniciou.
_X_OAUTH_COOKIE = "x_oauth_state"
_THREADS_OAUTH_COOKIE = "threads_oauth_state"
_INSTAGRAM_OAUTH_COOKIE = "instagram_oauth_state"
_TIKTOK_OAUTH_COOKIE = "tiktok_oauth_state"
_FACEBOOK_OAUTH_COOKIE = "facebook_oauth_state"


def _sign_oauth_state(
    user_id: int, extra: dict | None = None, *, profile_id: str | None = None,
) -> tuple[str, str]:
    """Gera um `state` aleatório + cookie assinado (JWT) pra CSRF binding
    do account-linking OAuth. Retorna (state, valor do cookie) — o
    state vai na URL de autorização (ecoado pelo provedor no
    /callback), o cookie guarda esse mesmo state (e `extra`, ex.
    code_verifier do PKCE do X) até o /callback validar os dois
    batendo. O perfil ativo também é fixado: uma autorização iniciada
    em um perfil não pode ser concluída em outro perfil da mesma conta."""
    state = secrets.token_urlsafe(16)
    payload = {
        "uid": user_id,
        "state": state,
        "profile_id": profile_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        **(extra or {}),
    }
    import jwt

    cookie_value = jwt.encode(payload, settings.api_secret_key, algorithm="HS256")
    return state, cookie_value


def _verify_oauth_state(
    request: Request,
    cookie_name: str,
    state: str | None,
    user_id: int,
    profile_id: str | None,
) -> dict | None:
    """Valida o cookie assinado do /authorize contra o `state` da query
    (CSRF) e o `user_id` da sessão atual. Retorna o payload decodificado
    (com `code_verifier`, se houver) ou None se inválido/ausente/
    expirado — o chamador trata None como falha de CSRF."""
    token = request.cookies.get(cookie_name)
    if not token or not state:
        return None
    import jwt

    try:
        decoded = jwt.decode_complete(
            token, settings.api_secret_key, algorithms=["HS256"]
        )
        header = decoded.get("header") or {}
        if "crit" in header:
            # RFC 7515 §4.1.11 / GHSA-752w-5fwx-jx9f: nenhuma extensão crítica é suportada
            return None
        payload = decoded.get("payload") or {}
    except Exception:
        return None
    if (
        payload.get("uid") != user_id
        or payload.get("state") != state
        or payload.get("profile_id") != profile_id
    ):
        return None
    return payload


@router.get("")
async def list_credentials(user_id: int = Depends(get_current_user_id), profile_id: str | None = Depends(get_current_profile_id)):
    """Status de conexão (sem valor) de todas as redes suportadas.

    O texto cru do teste (`check_message`, devolvido pela API da rede) nunca
    sai daqui, nem para ADMIN: só luz/estado/rótulo padronizados."""
    checks_row = (
        scope_owner(supabase.table("credential_checks").select("network, state, message, checked_at"), user_id, profile_id).execute()
    )
    checks_by_network = {c["network"]: c for c in (checks_row.data or [])}
    checks_by_network.update(_account_checks(user_id))

    result: dict[str, dict] = {}

    for network, table in SIMPLE_NETWORKS.items():
        query = scope_account(supabase.table(table).select("status"), user_id) if network == "shopee" else scope_owner(
            supabase.table(table).select("status"), user_id, profile_id,
        )
        row = query.maybe_single().execute()
        result[network] = _status_only(row.data if row else None, checks_by_network.get(network))

    # Threads/X/TikTok/Instagram são OAuth de app único: "conectado" tem que
    # significar "tem token de usuário", não "status" (que no caso do
    # Threads é setado junto com o token, mas nas outras 3 não existe mais
    # nenhum campo além do token — ver OAUTH_NETWORKS acima).
    for network, (table, token_field) in OAUTH_NETWORKS.items():
        expiry_cols = "".join(
            f", {c}" for c in (*_TOKEN_EXPIRY_FIELDS.get(network, ()), *_STATUS_EXTRA_COLUMNS.get(network, ()))
        )
        row = (
            scope_owner(supabase.table(table).select(f"status, {token_field}{expiry_cols}"), user_id, profile_id)
            .maybe_single().execute()
        )
        result[network] = _status_only(
            row.data if row else None, checks_by_network.get(network),
            token_field=token_field, network=network,
        )

    return result


def _require_admin(user_id: int = Depends(get_current_user_id)) -> int:
    """Restringe overrides manuais e diagnósticos administrativos.

    O status das conexões continua disponível para o dono do perfil, mas
    somente administradores podem inserir credenciais emitidas fora do OAuth.
    """
    result = (
        supabase.table("users").select("access").eq("id", user_id)
        .maybe_single().execute()
    )
    if not result or not result.data or result.data.get("access") != "ADMIN":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user_id


async def save_threads_credential(
    body: ThreadsCredentialBody,
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Override administrativo de Threads com token já emitido.

    Usuários comuns conectam Threads exclusivamente pelo OAuth do app.

    Rota literal registrada ANTES de "/{network}": no Starlette, rotas
    casam na ordem de registro, e "/{network}" aceitaria "threads" como
    valor de path param se viesse primeiro, roubando esta requisição.
    """
    _upsert_by_user("threads_credentials", user_id, {
        "t_user_id": body.t_user_id,
        "access_token": encrypt(body.access_token),
        "status": True,
    }, profile_id=profile_id)
    return {"connected": True}


@router.delete("/threads")
async def delete_threads_credential(user_id: int = Depends(get_current_user_id), profile_id: str | None = Depends(get_current_profile_id)):
    result = (
        scope_owner(supabase.table("threads_credentials")
        .update({"t_user_id": None, "access_token": None, "status": False}), user_id, profile_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}


def _require_oauth_config(label: str, *values) -> None:
    """503 claro quando falta env var do app único (ID/segredo/callback), em
    vez de montar URL de autorização com "None" que a rede rejeita com erro
    genérico. Só testa presença — nunca lê nem loga os valores."""
    if not all(values):
        logger.error("OAuth %s sem configuração do servidor completa (variável de ambiente ausente)", label)
        raise HTTPException(
            status_code=503,
            detail=f"Conexão com {label} indisponível: configuração do servidor incompleta",
        )


@router.get("/threads/authorize")
async def threads_authorize(
    response: Response,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """URL de autorização do OAuth do Threads (Meta) — o frontend redireciona
    o usuário pra cá. Gera `state` + cookie httponly assinado (CSRF
    binding do account-linking, 10 min) pro /callback validar."""
    _require_oauth_config("Threads", threads_oauth.APP_ID, threads_oauth.SECRET, threads_oauth.CALLBACK_URL)

    state, cookie_value = _sign_oauth_state(user_id, profile_id=profile_id)

    response.set_cookie(
        key=_THREADS_OAUTH_COOKIE,
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    log_action("threads_oauth_authorize", user_id=user_id)
    return {"url": threads_oauth.get_user_auth_url(state)}


@router.get("/threads/callback")
async def threads_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Callback do OAuth do Threads (Meta): ?code=&state= (sucesso) ou
    ?error= (usuário negou autorização, ou outra falha do lado do
    Meta) — mesma semântica de erro do fluxo antigo em
    web/routes/panel/credentials.py::credentials_threads_save.

    Valida o `state` contra o cookie assinado do /authorize (CSRF)
    ANTES de trocar code por token — ver docstring de
    _sign_oauth_state/_verify_oauth_state acima. Salva a credencial e
    redireciona (307) pro frontend com um indicador de sucesso/erro na
    query string — o frontend não recebe token nem detalhe de erro
    sensível.
    """
    frontend_redirect = f"{settings.frontend_url}/credentials"

    def _redirect(query: str) -> RedirectResponse:
        res = RedirectResponse(f"{frontend_redirect}?{query}", status_code=307)
        res.delete_cookie(_THREADS_OAUTH_COOKIE)
        return res

    if error:
        return _redirect(f"threads=error&message={quote(error, safe='')}")

    if not code:
        return _redirect("threads=error&message=missing_code")

    if not _verify_oauth_state(
        request, _THREADS_OAUTH_COOKIE, state, user_id, profile_id,
    ):
        return _redirect("threads=error&message=invalid_state")

    try:
        t_user_id, access_token = await threads_oauth.get_user_auth_id_token(code)
    except threads_oauth.ThreadsOAuthError:
        return _redirect("threads=error&message=oauth_failed")

    _upsert_by_user("threads_credentials", user_id, {
        "t_user_id": t_user_id,
        "access_token": encrypt(access_token),
        "status": True,
    }, profile_id=profile_id)
    log_action("threads_oauth_token_exchanged", user_id=user_id, profile_id=profile_id)

    return _redirect("threads=success")


@router.get("/instagram/authorize")
async def instagram_authorize(
    response: Response,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """URL de autorização do Facebook Login for Business — Instagram Graph
    API não tem OAuth próprio, publica via conta Business/Creator vinculada
    a uma Página do Facebook (ver api/instagram_oauth.py).

    App único da plataforma (INSTAGRAM_APP_ID/SECRET via env) — não
    depende de nenhuma credencial salva pelo usuário antes de conectar.

    Gera `state` + cookie httponly assinado (CSRF binding do
    account-linking, 10 min) pro /callback validar."""
    _require_oauth_config(
        "Instagram", instagram_oauth.APP_ID, instagram_oauth.SECRET,
        instagram_oauth.CALLBACK_URL, instagram_oauth.CONFIG_ID,
    )

    state, cookie_value = _sign_oauth_state(user_id, profile_id=profile_id)

    response.set_cookie(
        key=_INSTAGRAM_OAUTH_COOKIE,
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    log_action("instagram_oauth_authorize", user_id=user_id)
    return {"url": instagram_oauth.get_user_auth_url(state)}


@router.get("/instagram/callback")
async def instagram_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Callback do Facebook Login for Business pro Instagram: ?code=&state=
    (sucesso) ou ?error= (usuário negou autorização, ou outra falha do
    lado do Meta). Mesma semântica do callback do Threads acima.

    Valida o `state` contra o cookie assinado do /authorize (CSRF)
    ANTES de trocar code por token. Troca code por user_access_token de
    longa duração, resolve o ig_user_id (conta Instagram Business/
    Creator vinculada a alguma Página do usuário) e salva os dois —
    nunca expõe token/erro sensível pro frontend.
    """
    frontend_redirect = f"{settings.frontend_url}/credentials"

    def _redirect(query: str) -> RedirectResponse:
        res = RedirectResponse(f"{frontend_redirect}?{query}", status_code=307)
        res.delete_cookie(_INSTAGRAM_OAUTH_COOKIE)
        return res

    if error:
        return _redirect(f"instagram=error&message={quote(error, safe='')}")

    if not code:
        return _redirect("instagram=error&message=missing_code")

    if not _verify_oauth_state(
        request, _INSTAGRAM_OAUTH_COOKIE, state, user_id, profile_id,
    ):
        return _redirect("instagram=error&message=invalid_state")

    try:
        ig_user_id, access_token, fb_user_id = await instagram_oauth.get_user_auth_id_token(code)
    except instagram_oauth.InstagramOAuthError:
        logger.exception(
            "Falha na troca de code por token OAuth do Instagram para user_id=%s", user_id
        )
        return _redirect("instagram=error&message=oauth_failed")

    _upsert_by_user("instagram_credentials", user_id, {
        "ig_user_id": ig_user_id,
        "fb_user_id": fb_user_id,
        "user_access_token": encrypt(access_token),
        "status": True,
    }, profile_id=profile_id)
    log_action("instagram_oauth_token_exchanged", user_id=user_id, profile_id=profile_id)

    return _redirect("instagram=success")


@router.delete("/instagram")
async def delete_instagram_credential(user_id: int = Depends(get_current_user_id), profile_id: str | None = Depends(get_current_profile_id)):
    """Rota literal registrada ANTES de "/{network}" (ver docstring de
    save_threads_credential) — instagram saiu de SIMPLE_NETWORKS, então o
    handler genérico de DELETE não cobre mais essa rede."""
    result = (
        scope_owner(supabase.table("instagram_credentials")
        .update({"user_access_token": None, "ig_user_id": None, "fb_user_id": None, "status": False}), user_id, profile_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}


@router.get("/facebook/authorize")
async def facebook_authorize(
    response: Response,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """URL de autorização do Login do Facebook (mesmo app do Instagram,
    ver api/facebook_oauth.py). App único da plataforma — não depende de
    nenhuma credencial salva pelo usuário antes de conectar.

    Gera `state` + cookie httponly assinado (CSRF binding do
    account-linking, 10 min) pro /callback validar."""
    _require_oauth_config(
        "Facebook", instagram_oauth.APP_ID, instagram_oauth.SECRET,
        facebook_oauth.CALLBACK_URL, facebook_oauth.CONFIG_ID,
    )

    state, cookie_value = _sign_oauth_state(user_id, profile_id=profile_id)

    response.set_cookie(
        key=_FACEBOOK_OAUTH_COOKIE,
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    log_action("facebook_oauth_authorize", user_id=user_id)
    return {"url": facebook_oauth.get_user_auth_url(state)}


@router.get("/facebook/callback")
async def facebook_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Callback do Login do Facebook: ?code=&state= (sucesso) ou ?error=
    (usuário negou autorização, ou outra falha do lado do Meta). Mesma
    semântica dos callbacks de Threads/Instagram/TikTok/X acima.

    Valida o `state` contra o cookie assinado do /authorize (CSRF)
    ANTES de trocar code por token. Troca code por user_access_token,
    resolve a Página do usuário (primeira encontrada — ver limitação de
    múltiplas páginas em api/facebook_oauth.py) e salva page_id/page_name/
    page_access_token — nunca expõe token/erro sensível pro frontend.
    """
    frontend_redirect = f"{settings.frontend_url}/credentials"

    def _redirect(query: str) -> RedirectResponse:
        res = RedirectResponse(f"{frontend_redirect}?{query}", status_code=307)
        res.delete_cookie(_FACEBOOK_OAUTH_COOKIE)
        return res

    if error:
        return _redirect(f"facebook=error&message={quote(error, safe='')}")

    if not code:
        return _redirect("facebook=error&message=missing_code")

    if not _verify_oauth_state(
        request, _FACEBOOK_OAUTH_COOKIE, state, user_id, profile_id,
    ):
        return _redirect("facebook=error&message=invalid_state")

    try:
        page_id, page_name, page_access_token, fb_user_id = await facebook_oauth.get_user_auth_page_token(code)
    except facebook_oauth.FacebookOAuthError:
        logger.exception(
            "Falha na troca de code por token OAuth do Facebook para user_id=%s", user_id
        )
        return _redirect("facebook=error&message=oauth_failed")

    _upsert_by_user("facebook_credentials", user_id, {
        "page_id": page_id,
        "page_name": page_name,
        "fb_user_id": fb_user_id,
        "page_access_token": encrypt(page_access_token),
        "status": True,
    }, profile_id=profile_id)
    log_action("facebook_oauth_token_exchanged", user_id=user_id, profile_id=profile_id)

    return _redirect("facebook=success")


@router.delete("/facebook")
async def delete_facebook_credential(user_id: int = Depends(get_current_user_id), profile_id: str | None = Depends(get_current_profile_id)):
    """Rota literal registrada ANTES de "/{network}" (ver docstring de
    delete_instagram_credential) — facebook saiu de SIMPLE_NETWORKS."""
    result = (
        scope_owner(supabase.table("facebook_credentials")
        .update({
            "page_id": None,
            "page_name": None,
            "fb_user_id": None,
            "page_access_token": None,
            "status": False,
        }), user_id, profile_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}


# Verificação de propriedade de domínio pro TikTok Login Kit ("Verify URL
# prefix" no painel TikTok for Developers, app 7690297968163031048): o
# TikTok exige hospedar um arquivo com esse nome exato, nesse caminho
# exato (dentro do prefixo /credentials/tiktok/callback/ que registramos
# como redirect URI), antes de aceitar o app em modo produção — sem isso
# o "Conectar TikTok" nunca sai do modo Sandbox. Conteúdo gerado pelo
# próprio painel TikTok, não é segredo (só prova que o domínio é nosso).
# Rota registrada ANTES de /tiktok/callback e /tiktok/authorize — tem um
# segmento a mais no path (o nome do arquivo), então não conflita com
# nenhuma das duas, mas mantido perto por contexto.
@router.get("/tiktok/callback/tiktokiuKagbtH1lO37DxIynSn02EABvEKz1PM.txt")
async def tiktok_domain_verification():
    return PlainTextResponse(
        "tiktok-developers-site-verification=iuKagbtH1lO37DxIynSn02EABvEKz1PM"
    )


@router.get("/tiktok/callback/tiktoksuFLmrUFUxZQioEp5TCgDiOi0VAiY2e1.txt")
async def tiktok_domain_verification_staging_20261009():
    return PlainTextResponse(
        "tiktok-developers-site-verification=suFLmrUFUxZQioEp5TCgDiOi0VAiY2e1"
    )


@router.get("/tiktok/authorize")
async def tiktok_authorize(
    response: Response,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """URL de autorização do TikTok Login Kit.

    App único da plataforma (TIKTOK_CLIENT_KEY/SECRET via env) — não
    depende de nenhuma credencial salva pelo usuário antes de conectar.
    Ver docstring de api/tiktok_oauth.py.

    Gera `state` + cookie httponly assinado (CSRF binding do
    account-linking, 10 min) pro /callback validar.

    Sem gate de papel: usuário comum e admin conectam cada um a PRÓPRIA
    conta (state amarrado ao user_id da sessão).
    """
    if not tiktok_oauth.CLIENT_KEY or not tiktok_oauth.CALLBACK_URL:
        # Sem isso a URL saía com client_key=None / redirect_uri vazio e o
        # TikTok devolvia erro genérico na tela dele.
        logger.error("TikTok OAuth sem TIKTOK_CLIENT_KEY/TIKTOK_CALLBACK_URL configurados")
        raise HTTPException(status_code=503, detail="Conexão com TikTok indisponível no momento.")

    state, cookie_value = _sign_oauth_state(user_id, profile_id=profile_id)

    response.set_cookie(
        key=_TIKTOK_OAUTH_COOKIE,
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    log_action("tiktok_oauth_authorize", user_id=user_id)
    return {"url": tiktok_oauth.get_user_auth_url(state)}


@router.get("/tiktok/callback")
@router.get("/tiktok/callback/")
async def tiktok_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Callback do OAuth do TikTok: ?code=&state= (sucesso) ou ?error=
    (usuário negou autorização, ou outra falha do lado da TikTok).
    Mesma semântica dos callbacks de Threads/Instagram acima.

    Valida o `state` contra o cookie assinado do /authorize (CSRF)
    ANTES de trocar code por token. Usa o Client Key/Secret globais do
    app único (`api/tiktok_oauth.py`) — nunca expõe token nem detalhe
    de erro sensível pro frontend.

    Registrado nos DOIS formatos (com e sem barra final): a "Verify URL
    prefix" do TikTok Login Kit foi registrada como
    `.../credentials/tiktok/callback/` (com barra — ver comentário do
    arquivo de verificação de domínio logo acima), então o redirect_uri
    real que o TikTok ecoa de volta pode vir com barra final mesmo que
    TIKTOK_CALLBACK_URL não tenha. Antes desta rota só existir sem
    barra, o Starlette respondia a `/callback/` com um redirect_slashes
    307 automático — e como o processo interno (127.0.0.1:8001) não
    sabe que está atrás do proxy do Flask, o Location desse redirect
    vazava o host interno em vez do domínio público (mesmo bug já
    corrigido em products/lists/posts/users/credentials — ver docstring
    do módulo). Aceitar as duas variantes aqui elimina o redirect
    automático nesta rota, independente de qual formato exato o TikTok
    usar.
    """
    frontend_redirect = f"{settings.frontend_url}/credentials"

    def _redirect(query: str) -> RedirectResponse:
        res = RedirectResponse(f"{frontend_redirect}?{query}", status_code=307)
        res.delete_cookie(_TIKTOK_OAUTH_COOKIE)
        return res

    if error:
        return _redirect(f"tiktok=error&message={quote(error, safe='')}")

    if not code:
        return _redirect("tiktok=error&message=missing_code")

    if not _verify_oauth_state(
        request, _TIKTOK_OAUTH_COOKIE, state, user_id, profile_id,
    ):
        return _redirect("tiktok=error&message=invalid_state")

    try:
        access_token, refresh_token, open_id = await tiktok_oauth.get_user_auth_id_token(code)
    except tiktok_oauth.TikTokOAuthError:
        logger.exception(
            "Falha na troca de code por token OAuth do TikTok para user_id=%s", user_id
        )
        return _redirect("tiktok=error&message=oauth_failed")

    _upsert_by_user("tiktok_credentials", user_id, {
        "user_access_token": encrypt(access_token),
        "refresh_token": encrypt(refresh_token) if refresh_token else None,
        "open_id": open_id,
        "status": True,
    }, profile_id=profile_id)
    log_action("tiktok_oauth_token_exchanged", user_id=user_id, profile_id=profile_id)

    return _redirect("tiktok=success")


@router.delete("/tiktok")
async def delete_tiktok_credential(user_id: int = Depends(get_current_user_id), profile_id: str | None = Depends(get_current_profile_id)):
    """Rota literal registrada ANTES de "/{network}" — tiktok saiu de
    SIMPLE_NETWORKS, então o handler genérico de DELETE não cobre mais
    essa rede (ver docstring de delete_instagram_credential)."""
    result = (
        scope_owner(supabase.table("tiktok_credentials")
        .update({"user_access_token": None, "refresh_token": None, "open_id": None, "status": False}), user_id, profile_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}


@router.get("/x/authorize")
async def x_authorize(
    response: Response,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """URL de autorização OAuth 2.0 + PKCE do X.

    App único da plataforma (X_CLIENT_ID/SECRET via env) — não depende
    de nenhuma credencial salva pelo usuário antes de conectar. PKCE
    exige guardar o code_verifier gerado aqui até o /callback: vai num
    cookie httponly assinado (10 min).
    """
    _require_oauth_config("X", x_oauth.CLIENT_ID, x_oauth.CLIENT_SECRET, x_oauth.CALLBACK_URL)

    code_verifier, code_challenge = x_oauth.generate_pkce_pair()
    state, cookie_value = _sign_oauth_state(
        user_id, {"code_verifier": code_verifier}, profile_id=profile_id,
    )

    response.set_cookie(
        key=_X_OAUTH_COOKIE,
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    log_action("x_oauth_authorize", user_id=user_id)
    return {"url": x_oauth.get_user_auth_url(code_challenge, state)}


@router.get("/x/callback")
async def x_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Callback do OAuth 2.0 + PKCE do X: ?code=&state= (sucesso) ou
    ?error= (usuário negou autorização, ou outra falha do lado do X).
    Mesma semântica de erro dos callbacks de Threads/Instagram/TikTok
    acima.

    Valida o `state` contra o cookie assinado do /authorize (CSRF) e usa
    o code_verifier guardado nele pra trocar o code por
    access_token/refresh_token — nunca expõe token nem detalhe de erro
    sensível pro frontend.
    """
    frontend_redirect = f"{settings.frontend_url}/credentials"

    def _redirect(query: str) -> RedirectResponse:
        res = RedirectResponse(f"{frontend_redirect}?{query}", status_code=307)
        res.delete_cookie(_X_OAUTH_COOKIE)
        return res

    if error:
        return _redirect(f"x=error&message={quote(error, safe='')}")

    if not code:
        return _redirect("x=error&message=missing_code")

    oauth_state = _verify_oauth_state(
        request, _X_OAUTH_COOKIE, state, user_id, profile_id,
    )
    if not oauth_state:
        return _redirect("x=error&message=invalid_state")

    try:
        token_data = await x_oauth.exchange_code_for_token(code, oauth_state["code_verifier"])
    except x_oauth.XOAuthError:
        logger.exception(
            "Falha na troca de code por token OAuth do X para user_id=%s", user_id
        )
        return _redirect("x=error&message=oauth_failed")

    expires_in = token_data.get("expires_in", 7200)
    _upsert_by_user("x_credentials", user_id, {
        "user_access_token": encrypt(token_data["access_token"]),
        "user_refresh_token": encrypt(token_data.get("refresh_token")),
        "scope": token_data.get("scope") or None,
        "token_expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        ).isoformat(),
        "status": True,
    }, profile_id=profile_id)
    log_action("x_oauth_token_exchanged", user_id=user_id, profile_id=profile_id)

    return _redirect("x=success")


@router.delete("/x")
async def delete_x_credential(user_id: int = Depends(get_current_user_id), profile_id: str | None = Depends(get_current_profile_id)):
    """Rota literal registrada ANTES de "/{network}" — x saiu de
    SIMPLE_NETWORKS, então o handler genérico de DELETE não cobre mais
    essa rede (ver docstring de delete_instagram_credential)."""
    result = (
        scope_owner(supabase.table("x_credentials")
        .update({
            "user_access_token": None,
            "user_refresh_token": None,
            "scope": None,
            "token_expires_at": None,
            "status": False,
        }), user_id, profile_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}


# Overrides manuais admin-only pra debug/emergência (testar com uma conta
# específica sem completar o OAuth inteiro, ou recuperar de um estado
# quebrado) — mesmo padrão do PUT /credentials/threads (cola token já
# emitido), mas admin-only (mesma dependência de POST /{network}/test)
# porque o usuário comum nunca vê esses formulários (só o botão "Conectar").
# Path "/manual" (não literal "/x" etc)
# pra não roubar a rota PUT /{network} genérica (SIMPLE_NETWORKS) nem o
# teste que confirma que ela devolve 404 pra essas redes.
async def save_x_credential_manual(
    body: XManualCredentialBody,
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    _upsert_by_user("x_credentials", user_id, {
        "user_access_token": encrypt(body.user_access_token),
        "user_refresh_token": encrypt(body.user_refresh_token) if body.user_refresh_token else None,
        "scope": body.scope or None,
        "status": True,
    }, profile_id=profile_id)
    return {"connected": True}


async def save_facebook_credential_manual(
    body: FacebookManualCredentialBody,
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    _upsert_by_user("facebook_credentials", user_id, {
        "page_id": body.page_id,
        "page_name": body.page_name,
        "page_access_token": encrypt(body.page_access_token),
        "status": True,
    }, profile_id=profile_id)
    return {"connected": True}


async def save_tiktok_credential_manual(
    body: TikTokManualCredentialBody,
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    _upsert_by_user("tiktok_credentials", user_id, {
        "open_id": body.open_id,
        "user_access_token": encrypt(body.user_access_token),
        "refresh_token": encrypt(body.refresh_token) if body.refresh_token else None,
        "status": True,
    }, profile_id=profile_id)
    return {"connected": True}


async def save_instagram_credential_manual(
    body: InstagramManualCredentialBody,
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    _upsert_by_user("instagram_credentials", user_id, {
        "ig_user_id": body.ig_user_id,
        "user_access_token": encrypt(body.user_access_token),
        "status": True,
    }, profile_id=profile_id)
    return {"connected": True}


async def save_kwai_credential_manual(
    body: SimpleCredentialBody,
    user_id: int = Depends(_require_admin),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Override administrativo do Kwai (registrado só em /admin/credentials/kwai/manual)."""
    _upsert_by_user("kwai_credentials", user_id, {
        "app_id": body.app_id.strip(),
        "secret": encrypt(body.secret.strip()),
        "status": True,
    }, profile_id=profile_id)
    return {"connected": True}


# ── Chave de IA por usuário/perfil (Gemini/OpenAI/Anthropic) ──────────────────
# Sem chave global do servidor: cada usuário (admin ou comum) cadastra a
# própria; "Gerar texto com IA" (api/routers/posts.py) usa resolve_ai_key.
# O resultado do "Testar conexão" vai pra credential_checks com network
# "ai_<provedor>", mesma luz/estado das outras redes (_connection_state).

AI_TABLE = "ai_credentials"
_AI_KEY_MAX_LEN = 500


class AiCredentialBody(BaseModel):
    api_key: str
    model: str | None = None


def _ai_provider(provider: str) -> str:
    if provider not in ai_llm.PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provedor de IA '{provider}' não suportado")
    return provider


def _ai_rows(user_id, profile_id: str | None) -> list[dict]:
    return scope_account(
        supabase.table(AI_TABLE).select("provider, secret, model, status, updated_at"), user_id,
    ).execute().data or []


def resolve_ai_key(user_id, profile_id: str | None, provider: str | None = None) -> tuple[str, str, str | None]:
    """(provedor, chave decifrada, modelo) do usuário/perfil. Com `provider`,
    usa só aquele; sem, o único salvo ou o salvo mais recentemente. Nunca cai
    pra chave global: sem chave -> 400 acionável."""
    rows = [r for r in _ai_rows(user_id, profile_id) if r.get("status") and r.get("secret")]
    if provider:
        rows = [r for r in rows if r.get("provider") == _ai_provider(provider)]
    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma chave de IA cadastrada. Cadastre sua chave em Credenciais → Inteligência Artificial.",
        )
    row = max(rows, key=lambda r: str(r.get("updated_at") or ""))
    return row["provider"], decrypt(row["secret"]), row.get("model")


def _save_check(user_id, profile_id: str | None, network: str, state: str, message: str) -> str:
    checked_at = datetime.now(timezone.utc).isoformat()
    check_data = {"state": state, "message": message, "checked_at": checked_at}
    if _is_account_network(network):
        existing_rows = scope_account(
            supabase.table("credential_checks").select("id, checked_at"), user_id,
        ).eq("network", network).execute().data or []
        existing = _latest_check(existing_rows)
        if existing:
            supabase.table("credential_checks").update({**check_data, "profile_id": None}).eq(
                "id", existing["id"],
            ).eq("user_id", user_id).execute()
            duplicate_ids = [row["id"] for row in existing_rows if row["id"] != existing["id"]]
            if duplicate_ids:
                scope_account(supabase.table("credential_checks").delete(), user_id).eq(
                    "network", network,
                ).in_("id", duplicate_ids).execute()
        else:
            supabase.table("credential_checks").insert({
                **check_data, "user_id": user_id, "network": network,
            }).execute()
    else:
        existing = _scope_check(
            supabase.table("credential_checks").select("id"), user_id, profile_id, network,
        ).eq("network", network).maybe_single().execute()
        if existing and existing.data:
            supabase.table("credential_checks").update(check_data).eq(
                "id", existing.data["id"],
            ).eq("user_id", user_id).execute()
        else:
            supabase.table("credential_checks").insert({
                **check_data, "user_id": user_id, "network": network,
                **({"profile_id": profile_id} if profile_id else {}),
            }).execute()
    return checked_at


@router.get("/ai")
async def list_ai_credentials(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Status por provedor (sem a chave) + qual seria usado no "Gerar texto"."""
    rows = {r["provider"]: r for r in _ai_rows(user_id, profile_id)}
    checks_by_network = _account_checks(user_id)
    providers = {}
    for provider in ai_llm.PROVIDERS:
        row = rows.get(provider)
        status = _status_only(
            {"status": bool(row and row.get("status") and row.get("secret"))},
            checks_by_network.get(f"ai_{provider}"),
        )
        status["model"] = row.get("model") if row else None
        status["default_model"] = ai_llm.DEFAULT_MODELS[provider]
        providers[provider] = status
    connected = [rows[p] for p in rows if providers.get(p, {}).get("connected")]
    active = max(connected, key=lambda r: str(r.get("updated_at") or ""))["provider"] if connected else None
    return {"providers": providers, "active": active}


@router.put("/ai/{provider}")
async def save_ai_credential(
    provider: str,
    body: AiCredentialBody,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Salva (cifrada) a chave do provedor e dispara o teste automático em
    segundo plano (estado "testing" -> resultado). Nunca devolve nem loga a chave."""
    provider = _ai_provider(provider)
    api_key = body.api_key.strip()
    if not api_key or len(api_key) > _AI_KEY_MAX_LEN:
        raise HTTPException(status_code=400, detail="Informe uma chave de API válida.")
    model = (body.model or "").strip() or None
    if model and not ai_llm.valid_model(model):
        raise HTTPException(status_code=400, detail="Nome de modelo inválido.")

    data = {
        "secret": encrypt(api_key), "model": model, "status": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    existing = scope_account(
        supabase.table(AI_TABLE).select("id"), user_id,
    ).eq("provider", provider).execute().data or []
    if existing:
        result = supabase.table(AI_TABLE).update(data).eq(
            "id", existing[0]["id"],
        ).eq("user_id", user_id).execute()
    else:
        row = {**data, "user_id": user_id, "provider": provider}
        result = supabase.table(AI_TABLE).insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar a chave de IA")
    _start_autotest(f"ai_{provider}", user_id, profile_id)
    log_action("ai_credential_saved", provider, user_id=user_id, profile_id=profile_id)
    return {"connected": True}


@router.delete("/ai/{provider}")
async def delete_ai_credential(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Desconecta (apaga a chave cifrada, mantém a linha)."""
    provider = _ai_provider(provider)
    result = scope_account(
        supabase.table(AI_TABLE).update({"secret": None, "status": False}), user_id,
    ).eq("provider", provider).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Chave de IA não encontrada")
    scope_account(supabase.table("credential_checks").delete(), user_id).eq(
        "network", f"ai_{provider}").execute()
    log_action("ai_credential_deleted", provider, user_id=user_id, profile_id=profile_id)
    return {"connected": False}


@router.post("/ai/{provider}/test")
async def test_ai_credential(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Chamada mínima ao provedor com a chave do próprio usuário/perfil."""
    provider = _ai_provider(provider)
    _check_test_rate_limit(user_id)
    _, api_key, model = resolve_ai_key(user_id, profile_id, provider)
    try:
        await run_in_threadpool(ai_llm.check_key, provider, api_key, model)
        state, message = "ok", "Chave funcionando"
    except ai_llm.LLMError as e:
        state, message = "error", str(e)
    checked_at = _save_check(user_id, profile_id, f"ai_{provider}", state, message)
    light, conn_state, status_text = _connection_state(True, {"state": state, "message": message})
    return {
        "light": light, "state": conn_state, "status_text": status_text,
        "message": message, "checked_at": checked_at,
    }


_TEST_NETWORKS = {**SIMPLE_NETWORKS, **{n: t for n, (t, _) in OAUTH_NETWORKS.items()}}

# App único da plataforma pra cada rede OAuth — app_id/secret vêm de env
# (ver api/x_oauth.py, api/tiktok_oauth.py, api/instagram_oauth.py), não
# mais da credencial do usuário. Threads não entra aqui: seu teste só
# usa o access_token (ver ramo dedicado abaixo).
_OAUTH_GLOBAL_APP = {
    "x": (x_oauth.CLIENT_ID, x_oauth.CLIENT_SECRET),
    "tiktok": (tiktok_oauth.CLIENT_KEY, tiktok_oauth.CLIENT_SECRET),
    "instagram": (instagram_oauth.APP_ID, instagram_oauth.SECRET),
}


# Colunas extras lidas pro teste: coluna -> (chave no payload, cifrada?).
# O refresh token deixa o teste renovar um access token expirado (X ~2h,
# TikTok ~24h); ig_user_id é a conta Instagram Business já resolvida no OAuth.
_TEST_EXTRA_COLUMNS = {
    "x": {"user_refresh_token": ("refresh_token", True)},
    "tiktok": {"refresh_token": ("refresh_token", True)},
    "instagram": {"ig_user_id": ("ig_user_id", False)},
}


def _persist_refreshed_tokens(network: str, user_id, profile_id: str | None, tokens: dict | None) -> None:
    """Grava os tokens que o teste renovou. Refresh token rotaciona (X): se
    não persistir, o próximo uso falha mesmo com o teste "verde"."""
    if not tokens or not tokens.get("access_token"):
        return
    data = {"user_access_token": encrypt(tokens["access_token"])}
    refresh_column = "user_refresh_token" if network == "x" else "refresh_token"
    if network == "x" and tokens.get("scope"):
        data["scope"] = tokens["scope"]
    if tokens.get("refresh_token"):
        data[refresh_column] = encrypt(tokens["refresh_token"])
    if network == "x" and tokens.get("expires_in"):
        data["token_expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=int(tokens["expires_in"]))
        ).isoformat()
    table = _TEST_NETWORKS[network]
    try:
        (scope_account(supabase.table(table).update(data), user_id) if network == "shopee" else scope_owner(
            supabase.table(table).update(data), user_id, profile_id,
        )).execute()
    except Exception as e:
        logger.warning("teste %s: não gravou tokens renovados: %s", network, type(e).__name__)


def _test_payload(network: str, user_id: int, profile_id: str | None = None) -> dict | None:
    """Busca e descriptografa só os campos necessários pra chamar a API
    real da rede via bridge interno (ver web/routes/internal.py). None
    quando não há credencial suficiente pra testar (endpoint trata como
    400 — nada foi salvo ainda, luz já é 'red' sem precisar chamar nada)."""
    table = _TEST_NETWORKS.get(network)
    if not table:
        raise HTTPException(status_code=404, detail=f"Rede '{network}' não suportada")

    if network == "threads":
        row = (
            scope_owner(supabase.table(table).select("access_token"), user_id, profile_id).maybe_single().execute()
        )
        data = row.data if row and row.data else None
        if not data or not data.get("access_token"):
            return None
        return {"access_token": decrypt(data["access_token"])}

    if network == "facebook":
        # Sem app_id/secret aqui — o app é global (mesmo de
        # api/instagram_oauth.py) e o que importa pra testar é só o
        # token JÁ escopado pra Página do usuário (ver
        # api/facebook_oauth.py).
        row = (
            scope_owner(supabase.table(table).select("page_id, page_access_token"), user_id, profile_id).maybe_single().execute()
        )
        data = row.data if row and row.data else None
        token = data.get("page_access_token") if data else None
        if not token:
            return None
        return {"page_id": data.get("page_id"), "page_access_token": decrypt(token)}

    if network in _OAUTH_GLOBAL_APP:
        app_id, secret = _OAUTH_GLOBAL_APP[network]
        if not app_id or not secret:
            # App único ainda não configurado no servidor (env var
            # ausente) — nada a testar, mesmo efeito de "credencial não
            # salva" pro usuário (luz fica vermelha).
            return None
        extra = _TEST_EXTRA_COLUMNS.get(network, {})
        columns = ", ".join(["user_access_token", *extra])
        row = (
            scope_owner(supabase.table(table).select(columns), user_id, profile_id).maybe_single().execute()
        )
        data = row.data if row and row.data else {}
        payload: dict = {"app_id": app_id, "secret": secret}
        if data.get("user_access_token"):
            payload["user_access_token"] = decrypt(data["user_access_token"])
        for column, (key, encrypted) in extra.items():
            if data.get(column):
                payload[key] = decrypt(data[column]) if encrypted else data[column]
        return payload

    query = scope_account(supabase.table(table).select("app_id, secret"), user_id) if network == "shopee" else scope_owner(
        supabase.table(table).select("app_id, secret"), user_id, profile_id,
    )
    row = query.maybe_single().execute()
    data = row.data if row and row.data else None
    if not data or not data.get("app_id") or not data.get("secret"):
        return None

    return {"app_id": data["app_id"], "secret": decrypt(data["secret"])}


# ── Teste automático pós-salvar/reconectar ───────────────────────────────────
# Salvar grava credential_checks.state="testing" (síncrono, então o GET
# seguinte já mostra "Testando…") e um worker faz o teste real (mesma chamada
# do botão "Testar conexão"). Não passa pelo rate limit manual: vários saves
# seguidos precisam testar todos. Qualquer falha vira state="error".
_AUTOTEST_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cred-autotest")


def _autotest_submit(fn, *args) -> None:
    _AUTOTEST_EXECUTOR.submit(fn, *args)


def _call_with_timeout(fn, *args):
    """Roda `fn` num thread descartável e desiste após AUTOTEST_TIMEOUT_SECONDS
    (o thread órfão termina sozinho pelo timeout HTTP do provedor)."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(fn, *args).result(timeout=AUTOTEST_TIMEOUT_SECONDS)
    finally:
        pool.shutdown(wait=False)


def _autotest_outcome(network: str, user_id, profile_id: str | None) -> tuple[str, str]:
    if network.startswith("ai_"):
        _, api_key, model = resolve_ai_key(user_id, profile_id, network[3:])
        try:
            _call_with_timeout(ai_llm.check_key, network[3:], api_key, model)
        except ai_llm.LLMError as e:
            return "error", str(e)
        return "ok", "Chave funcionando"
    payload = _test_payload(network, user_id, profile_id)
    if payload is None:
        return "error", "Credencial incompleta — nada para testar"
    result = _call_with_timeout(
        lambda: asyncio.run(validate_network_credential(network, payload)),
    )
    _persist_refreshed_tokens(network, user_id, profile_id, result.get("refreshed_tokens"))
    return result.get("state") or "error", result.get("message") or ""


def _run_autotest(network: str, user_id, profile_id: str | None, started_at: str) -> None:
    try:
        state, message = _autotest_outcome(network, user_id, profile_id)
    except FutureTimeout:
        state, message = "error", "O teste excedeu o tempo limite"
    except HTTPException as e:
        state, message = "error", str(e.detail)
    except InternalApiError:
        state, message = "error", "Não foi possível testar a conexão agora"
    except Exception as e:  # nunca deixar o selo preso em "Testando…"
        logger.warning("autotest %s falhou: %s", network, type(e).__name__)
        state, message = "error", "Falha inesperada ao testar"
    try:
        _finish_check(user_id, profile_id, network, started_at, state, message)
    except Exception as e:
        logger.warning("autotest %s: não gravou resultado: %s", network, type(e).__name__)


def _finish_check(user_id, profile_id: str | None, network: str, started_at: str, state: str, message: str) -> None:
    """Grava o resultado só se a linha ainda é o MESMO "testing" que este
    worker iniciou (credencial regravada/desconectada/testada à mão no meio
    do caminho = resultado velho, descartado)."""
    row = _scope_check(
        supabase.table("credential_checks").select("id, state, checked_at"), user_id, profile_id, network,
    ).eq("network", network).maybe_single().execute()
    current = row.data if row else None
    if not current or current.get("state") != "testing":
        return
    if _parse_ts(current.get("checked_at")) != _parse_ts(started_at):
        return
    supabase.table("credential_checks").update({
        "state": state, "message": message, "checked_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", current["id"]).eq("user_id", user_id).execute()


def _start_autotest(network: str, user_id, profile_id: str | None) -> None:
    """Best-effort: o save já foi feito, então falha aqui não derruba a
    resposta — o selo cai em "nunca testada" e o botão manual continua."""
    try:
        started_at = _save_check(user_id, profile_id, network, "testing", "")
        _autotest_submit(_run_autotest, network, user_id, profile_id, started_at)
    except Exception as e:
        logger.warning("autotest %s: não iniciou: %s", network, type(e).__name__)


# ponytail: rate limit em memória de processo (mesmo padrão de
# catalog.py/auth.py) — 1 worker hoje; Redis se virar multi-instância.
_TEST_RATE_LIMIT_ATTEMPTS = 6
_TEST_RATE_LIMIT_WINDOW_SECONDS = 60
_test_attempts: dict = {}


def _check_test_rate_limit(user_id) -> None:
    now = time.monotonic()
    attempts = [t for t in _test_attempts.get(user_id, []) if now - t < _TEST_RATE_LIMIT_WINDOW_SECONDS]
    if len(attempts) >= _TEST_RATE_LIMIT_ATTEMPTS:
        _test_attempts[user_id] = attempts
        raise HTTPException(status_code=429, detail="Muitos testes em pouco tempo. Aguarde um minuto.")
    _test_attempts[user_id] = attempts + [now]


@router.post("/{network}/test")
async def test_credential(network: str, user_id: int = Depends(get_current_user_id), profile_id: str | None = Depends(get_current_profile_id)):
    """"Testar conexão" — chama a API real da rede (via bridge interno) e
    grava o resultado em credential_checks, que é o que alimenta a luz do
    sinalizador (GET /credentials). Qualquer usuário testa a PRÓPRIA
    credencial (escopo user_id/perfil em _test_payload — nunca a de outro),
    com rate limit pra não gastar chamada real à toa."""
    _check_test_rate_limit(user_id)
    payload = _test_payload(network, user_id, profile_id)
    if payload is None:
        raise HTTPException(status_code=400, detail="Nenhuma credencial salva para esta rede.")

    try:
        result = await validate_network_credential(network, payload)
    except InternalApiError:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível testar a conexão agora. Tente novamente.",
        )

    _persist_refreshed_tokens(network, user_id, profile_id, result.get("refreshed_tokens"))
    state = result.get("state") or "error"
    message = result.get("message") or ""
    checked_at = _save_check(user_id, profile_id, network, state, message)

    light, conn_state, status_text = _connection_state(True, {"state": state, "message": message})
    return {
        "light": light, "state": conn_state, "status_text": status_text,
        "message": status_text if conn_state != "ok" else message, "checked_at": checked_at,
    }


@router.put("/{network}")
async def save_credential(
    network: str,
    body: SimpleCredentialBody,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Cria ou atualiza a credencial (update-or-insert por user_id). Cifra o secret."""
    if network == "kwai":
        # Override manual: PUT /admin/credentials/kwai/manual.
        raise HTTPException(status_code=404, detail="Rede não suportada")
    table = _simple_table(network)

    # .strip(): copiar/colar do painel da rede (Shopee Affiliate, Meta for
    # Developers) facilmente traz espaço em branco líder/de trás — isso
    # quebra client_id=/app_id= sem nenhum erro visível (bug encontrado em
    # produção no TikTok, quando ainda era per-user; mantido aqui porque
    # Shopee/Facebook continuam colados à mão). Aplicado a TODAS as redes
    # de SIMPLE_NETWORKS.
    app_id = body.app_id.strip()
    secret = body.secret.strip()

    if network == "shopee":
        try:
            valid = await validate_shopee_credential(app_id, secret)
        except InternalApiError:
            raise HTTPException(
                status_code=502,
                detail="Não foi possível validar a credencial da Shopee agora. Tente novamente.",
            )
        if not valid:
            raise HTTPException(status_code=400, detail="Credencial da Shopee inválida")

    data = {
        "app_id": app_id,
        "secret": encrypt(secret),
        "status": True,
    }

    _upsert_by_user(table, user_id, data, profile_id=profile_id)
    return {"connected": True}


@router.delete("/{network}")
async def delete_credential(
    network: str,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Desconecta (zera app_id/secret, status=False) — não apaga a linha.

    Só cobre SIMPLE_NETWORKS (shopee/kwai) — x/tiktok/instagram/facebook
    têm DELETE dedicado (delete_x_credential/delete_tiktok_credential/
    delete_instagram_credential/delete_facebook_credential, registrados
    antes desta rota) porque saíram de SIMPLE_NETWORKS na migração pro
    app único."""
    table = _simple_table(network)
    if network == "kwai":
        _require_admin(user_id)
    update_data = {"app_id": None, "secret": None, "status": False}
    query = scope_account(supabase.table(table).update(update_data), user_id) if network == "shopee" else scope_owner(
        supabase.table(table).update(update_data), user_id, profile_id,
    )
    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}

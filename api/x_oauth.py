"""
OAuth 2.0 + PKCE do X (Twitter) — API Python (FastAPI).

Duplica as funções OAuth puras de `apis/x.py` (mesmos endpoints, mesmos
parâmetros) em vez de importar entre módulos — mesmo padrão de
`api/threads_oauth.py`: evita que a API nova dependa de
`shopee_bot.utils` (apis/x.py importa `retry_with_backoff` no nível do
módulo só por causa das funções de publicação).

App único da plataforma (mesmo padrão de api/threads_oauth.py): Rafa
registra UM app no X Developer Portal, client_id/client_secret vêm de
env (X_CLIENT_ID/X_CLIENT_SECRET) — o usuário final só clica "Conectar
X" e autoriza, nunca vê nem cola client_id/secret de app nenhum. Antes
disso cada usuário cadastrava o próprio app (per-user); migrado pro app
único pra simplificar pro usuário leigo (decisão + rollout documentados
no vault, ver Projetos/ShopeeAutoVendas/27-Migracao-App-Unico-OAuth.md).

BLOQUEIO EXTERNO: o app do X (o ÚNICO, de Rafa) precisa ter "User
authentication settings" (OAuth 2.0) habilitado no X Developer Portal,
com o redirect URI abaixo cadastrado — e pode exigir tier pago
dependendo do volume de posts. Sem isso, exchange_code_for_token /
refresh_access_token chegam a rodar mas recebem erro do lado do X.
Ver docstring completa em apis/x.py.
"""

import base64
import hashlib
import logging
import os
import secrets
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("uvicorn.error")

AUTH_URL = "https://twitter.com/i/oauth2/authorize"
# api.x.com é o host canônico atual (api.twitter.com é o domínio legado
# pós-rebranding) — usar direto evita qualquer redirect cross-host, que o
# httpx (por padrão, e explicitamente aqui via follow_redirects=False) não
# segue e que, se seguido, derruba o header Authorization (RFC-compliant
# strip de auth em redirect cross-host, mesmo comportamento do curl).
TOKEN_URL = "https://api.x.com/2/oauth2/token"
CALLBACK_URL = os.environ.get("X_CALLBACK_URL")
# .strip() defensivo: Render (e outros dashboards de env var) deixa
# passar espaço/newline colado no valor, o que vaza pro Basic Auth
# base64 e vira 401 "unauthorized_client / Missing valid authorization
# header" (header presente mas garbled) em vez do invalid_client que
# credencial errada daria. Ver .strip() equivalente em save_credential
# (commit 0d5f0b0) pra credenciais salvas no banco — este cobre a
# leitura via env var, caminho de código diferente.
CLIENT_ID = (os.environ.get("X_CLIENT_ID") or "").strip() or None
CLIENT_SECRET = (os.environ.get("X_CLIENT_SECRET") or "").strip() or None
DEFAULT_SCOPES = "tweet.read tweet.write users.read media.write offline.access"
MEDIA_SCOPE = "media.write"
MEDIA_RECONNECT_MESSAGE = (
    "X: reconecte o X para liberar imagens (a conexão atual não tem a "
    "permissão media.write)"
)


def has_media_write(scope: str | None) -> bool:
    """`scope` é o texto devolvido pelo X (separado por espaço). NULL/vazio =
    conexão antiga, escopo desconhecido: trata como sem media.write até
    reconectar (ou até um refresh devolver o escopo real)."""
    return MEDIA_SCOPE in (scope or "").split()


class XOAuthError(Exception):
    pass


def generate_pkce_pair() -> tuple[str, str]:
    """Gera (code_verifier, code_challenge) para o fluxo PKCE (S256)."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def get_user_auth_url(code_challenge: str, state: str, scopes: str = DEFAULT_SCOPES) -> str:
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK_URL,
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _basic_auth_header() -> dict:
    # .strip() de novo aqui (além do módulo): ponto único por onde os
    # dois callers (exchange_code_for_token, refresh_access_token)
    # passam — garante que nenhuma whitespace residual (ex.: atribuição
    # direta a CLIENT_ID/CLIENT_SECRET fora do os.environ.get() do
    # topo do arquivo) vaze pro Basic Auth.
    client_id = (CLIENT_ID or "").strip()
    client_secret = (CLIENT_SECRET or "").strip()
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


async def exchange_code_for_token(code: str, code_verifier: str) -> dict:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        **_basic_auth_header(),
    }
    # client_id NÃO vai no body: RFC 6749 §3.2.1 diz que um confidential
    # client não deve se autenticar por mais de um método na mesma
    # requisição. client_id no body + Basic Auth no header ao mesmo tempo
    # é redundante e o X rejeita com 401 unauthorized_client / "Missing
    # valid authorization header" (mesmo com o header presente e correto).
    # Autenticação do client é só via header Basic (_basic_auth_header).
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CALLBACK_URL,
        "code_verifier": code_verifier,
    }
    logger.info(
        "x_oauth.exchange_code_for_token: POST %s headers=%s body_keys=%s",
        TOKEN_URL,
        list(headers.keys()),
        list(body.keys()),
    )
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        res = await client.post(TOKEN_URL, headers=headers, data=body)
    if res.status_code not in (200, 201):
        raise XOAuthError(
            f"Failed to Exchange Code for Token: {res.status_code} {res.text}"
        )
    return res.json()


async def refresh_access_token(refresh_token: str) -> dict:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        **_basic_auth_header(),
    }
    # Mesmo tratamento de exchange_code_for_token: sem client_id no body,
    # autenticação do client só via header Basic.
    body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    logger.info(
        "x_oauth.refresh_access_token: POST %s headers=%s body_keys=%s",
        TOKEN_URL,
        list(headers.keys()),
        list(body.keys()),
    )
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        res = await client.post(TOKEN_URL, headers=headers, data=body)
    if res.status_code not in (200, 201):
        raise XOAuthError(
            f"Failed to Refresh Access Token: {res.status_code} {res.text}"
        )
    return res.json()

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
import os
import secrets
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
CALLBACK_URL = os.environ.get("X_CALLBACK_URL")
CLIENT_ID = os.environ.get("X_CLIENT_ID")
CLIENT_SECRET = os.environ.get("X_CLIENT_SECRET")
DEFAULT_SCOPES = "tweet.read tweet.write users.read offline.access"


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
    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


async def exchange_code_for_token(code: str, code_verifier: str) -> dict:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        **_basic_auth_header(),
    }
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CALLBACK_URL,
        "code_verifier": code_verifier,
        "client_id": CLIENT_ID,
    }
    async with httpx.AsyncClient(timeout=15) as client:
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
    body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(TOKEN_URL, headers=headers, data=body)
    if res.status_code not in (200, 201):
        raise XOAuthError(
            f"Failed to Refresh Access Token: {res.status_code} {res.text}"
        )
    return res.json()

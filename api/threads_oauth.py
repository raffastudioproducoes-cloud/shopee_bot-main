"""
OAuth do Threads (Meta) — API Python (FastAPI).

Duplica as funções OAuth puras de `apis/threads.py` (mesma URL, mesmos
parâmetros, mesmo fluxo) em vez de importar entre módulos: o padrão já
usado no projeto pra código compartilhado entre o Flask antigo e a API
nova é duplicar, não importar cross-módulo (ver api/crypto.py). Aqui
isso também evita que a API nova dependa de `shopee_bot.utils` (as
funções de POST de `apis/threads.py` usam `retry_with_backoff`; as de
OAuth, não).

Só o essencial pro fluxo de login (authorize URL, troca de code por
token, user id). Publicação de post e refresh de token continuam
exclusivos do Flask por enquanto.
"""

import os
from urllib.parse import quote

import httpx

API_URL = "https://graph.threads.net"
API_VERSION = "v1.0"
APP_ID = os.environ.get("THREADS_APP_ID")
SECRET = os.environ.get("THREADS_SECRET")
# Falta de default aqui (ao contrário de X/TikTok/Instagram/Facebook, que
# têm fallback hardcoded) fazia cair em scope=None quando a env var não
# tava setada — a Meta então não reconhecia um scope OAuth válido e o
# /oauth/authorize virava navegação normal pro app (feed pessoal) em vez
# de mostrar a tela de consentimento. threads_basic + threads_content_publish
# são os escopos oficiais mínimos pra login + publicação na Threads API.
PERMISSIONS = os.environ.get("THREADS_PERMISSIONS", "threads_basic,threads_content_publish")
CALLBACK_URL = os.environ.get("THREADS_CALLBACK_URL")


class ThreadsOAuthError(Exception):
    pass


def get_user_auth_url(state: str) -> str:
    # o primeiro passo não usa o subdomínio "graph", só os seguintes
    # https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions#etapa-1--receber-autoriza--o
    #
    # `state` é ecoado pelo Meta de volta no /callback — usado pelo
    # router (api/routers/credentials.py) pra CSRF binding do
    # account-linking (evita que um atacante induza a vítima a linkar a
    # conta social DELE à conta da vítima).
    return (
        "https://threads.net/oauth/authorize"
        f"?client_id={APP_ID}"
        f"&redirect_uri={quote(CALLBACK_URL or '', safe='')}"
        f"&scope={PERMISSIONS}"
        "&response_type=code"
        f"&state={quote(state, safe='')}"
    )


async def _get_user_short_lived_token(code: str) -> dict:
    # https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions#etapa-2--trocar-o-c-digo-por-um-token
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/oauth/access_token",
            params={
                "client_id": APP_ID,
                "client_secret": SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": CALLBACK_URL,
                "code": code,
            },
        )
    if res.status_code not in (200, 201):
        raise ThreadsOAuthError(
            f"Failed to Get User Short-Lived Access Token: {res.status_code} {res.text}"
        )
    return res.json()


async def _get_user_long_lived_token(short_lived_access_token: str) -> dict:
    # https://developers.facebook.com/docs/threads/get-started/long-lived-tokens
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/access_token",
            params={
                "client_secret": SECRET,
                "grant_type": "th_exchange_token",
                "access_token": short_lived_access_token,
            },
        )
    if res.status_code not in (200, 201):
        raise ThreadsOAuthError(
            f"Failed to Get User Long-Lived Access Token: {res.status_code} {res.text}"
        )
    return res.json()


async def get_user_auth_id_token(code: str) -> tuple[str, str]:
    user_data = await _get_user_short_lived_token(code)
    user_id = user_data["user_id"]
    short_lived_token = user_data["access_token"]

    token_data = await _get_user_long_lived_token(short_lived_token)
    access_token = token_data["access_token"]

    return user_id, access_token


async def get_user_id(user_access_token: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/{API_VERSION}/me",
            params={"access_token": user_access_token},
        )
    if res.status_code not in (200, 201):
        raise ThreadsOAuthError(f"Failed to Get User ID: {res.status_code} {res.text}")
    return res.json()["id"]

"""
OAuth do Instagram via Facebook Login for Business — API Python (FastAPI).

Instagram Graph API não tem login próprio: publicação exige uma conta
Instagram Business/Creator vinculada a uma Página do Facebook, e o token
vem do fluxo OAuth do Facebook (Login for Business) com os escopos
instagram_basic, instagram_content_publish e pages_show_list.

Mesmo padrão de `api/threads_oauth.py` (duplica o essencial do fluxo em
vez de importar `apis/instagram.py`, que depende de `shopee_bot.utils`).

Diferença importante em relação ao Threads: o App ID/Secret do Instagram
não é um único app global (INSTAGRAM_APP_ID/SECRET via env) — cada
usuário cadastra seu próprio app no Meta for Developers e já salvou
App ID/Secret via PUT /credentials/instagram (tabela
instagram_credentials, colunas app_id/secret). Por isso as funções aqui
recebem app_id/secret como parâmetro, puxados da credencial do usuário
no router, em vez de ler de variável de ambiente — mesmo padrão de
`api/tiktok_oauth.py`.

BLOQUEIO EXTERNO: publicar de verdade (instagram_content_publish) exige
App Review da Meta — processo separado, mesmo Meta Developer Console.
Até isso sair, só funciona com contas de tester do app. Isso não
bloqueia o código: authorize/callback funcionam normalmente, só a
chamada real de media_publish falha pra quem não é tester.
"""

import os
from urllib.parse import quote

import httpx

API_URL = "https://graph.facebook.com"
API_VERSION = "v19.0"
PERMISSIONS = os.environ.get(
    "INSTAGRAM_PERMISSIONS",
    "instagram_basic,instagram_content_publish,pages_show_list",
)
CALLBACK_URL = os.environ.get("INSTAGRAM_CALLBACK_URL")


class InstagramOAuthError(Exception):
    pass


def get_user_auth_url(app_id: str, state: str) -> str:
    # https://developers.facebook.com/docs/facebook-login/guides/access-tokens#get-a-user-access-token
    #
    # `state` é ecoado pelo Meta de volta no /callback — usado pelo
    # router (api/routers/credentials.py) pra CSRF binding do
    # account-linking (evita que um atacante induza a vítima a linkar a
    # conta social DELE à conta da vítima).
    return (
        f"https://www.facebook.com/{API_VERSION}/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={quote(CALLBACK_URL or '', safe='')}"
        f"&scope={PERMISSIONS}"
        "&response_type=code"
        f"&state={quote(state, safe='')}"
    )


async def _get_user_short_lived_token(app_id: str, secret: str, code: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/{API_VERSION}/oauth/access_token",
            params={
                "client_id": app_id,
                "client_secret": secret,
                "redirect_uri": CALLBACK_URL,
                "code": code,
            },
        )
    if res.status_code not in (200, 201):
        raise InstagramOAuthError(
            f"Failed to Get User Short-Lived Access Token: {res.status_code} {res.text}"
        )
    return res.json()["access_token"]


async def _get_user_long_lived_token(app_id: str, secret: str, short_lived_access_token: str) -> str:
    # https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/{API_VERSION}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": secret,
                "fb_exchange_token": short_lived_access_token,
            },
        )
    if res.status_code not in (200, 201):
        raise InstagramOAuthError(
            f"Failed to Get User Long-Lived Access Token: {res.status_code} {res.text}"
        )
    return res.json()["access_token"]


async def get_ig_user_id(user_access_token: str) -> str:
    """Percorre as Páginas do Facebook do usuário até achar uma com conta
    Instagram Business/Creator vinculada, e retorna o id dessa conta
    (ig-user-id usado em /{ig-user-id}/media)."""
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/{API_VERSION}/me/accounts",
            params={
                "fields": "id,name,instagram_business_account",
                "access_token": user_access_token,
            },
        )
    if res.status_code not in (200, 201):
        raise InstagramOAuthError(
            f"Failed to Get Facebook Pages: {res.status_code} {res.text}"
        )
    for page in res.json().get("data", []):
        ig_account = page.get("instagram_business_account")
        if ig_account and ig_account.get("id"):
            return ig_account["id"]
    raise InstagramOAuthError(
        "Nenhuma Página do Facebook do usuário tem conta Instagram "
        "Business/Creator vinculada."
    )


async def get_user_auth_id_token(app_id: str, secret: str, code: str) -> tuple[str, str]:
    """Troca o code do callback por um user_access_token de longa duração
    e o ig_user_id da conta Instagram vinculada. Retorna (ig_user_id,
    access_token)."""
    short_lived_token = await _get_user_short_lived_token(app_id, secret, code)
    access_token = await _get_user_long_lived_token(app_id, secret, short_lived_token)
    ig_user_id = await get_ig_user_id(access_token)
    return ig_user_id, access_token

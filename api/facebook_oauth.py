"""
OAuth do Facebook Login for Business — publicação em Página do Facebook.
API Python (FastAPI).

Reaproveita o MESMO app do Meta já usado por api/instagram_oauth.py
(INSTAGRAM_APP_ID/INSTAGRAM_SECRET) — é o mesmo produto "Login do
Facebook para Empresas" no painel do Meta for Developers, só que com
outro conjunto de permissões (pages_show_list/pages_read_engagement/
pages_manage_posts em vez de instagram_basic/instagram_content_publish).
Evita pedir pro Rafa cadastrar um segundo app no Meta só pra isso — só
precisa adicionar mais um redirect URI na mesma tela "Login do Facebook
para Empresas → Configurações" já usada pro Instagram.

App único da plataforma (mesmo padrão de api/instagram_oauth.py):
usuário final só clica "Conectar Facebook" e autoriza, nunca vê nem
cola App ID/Secret de app nenhum.

Resolve o problema de arquitetura documentado em apis/facebook.py e no
vault (Projetos/ShopeeAutoVendas/27-Migracao-App-Unico-OAuth.md, seção
"Facebook — adiado"): antes, o Page Access Token era derivado de um App
Access Token (client_credentials) + /me/accounts, que só enxerga
Páginas que o PRÓPRIO app administra — não as de um usuário qualquer do
SaaS. Agora o token vem do /me/accounts do USUÁRIO autenticado (mesmo
padrão que api/instagram_oauth.py::get_ig_user_id já usava), então
funciona pra Páginas de qualquer usuário que autorizar.

BLOQUEIO EXTERNO: publicar de fato (pages_manage_posts) exige App
Review da Meta — mesma limitação já documentada em apis/facebook.py.
Até isso sair, só funciona com Páginas onde o usuário é Admin/Tester do
app.

LIMITAÇÃO CONHECIDA (MVP): se o usuário administra mais de uma Página
do Facebook, conecta automaticamente a PRIMEIRA da lista devolvida pela
Graph API — ainda não tem seletor de página. Ver vault pra evoluir isso
(deixar o usuário escolher, igual poderia ser feito pro Instagram).
"""

import os
from urllib.parse import quote

import httpx

from apis.meta_version import GRAPH_URL, GRAPH_VERSION

from . import instagram_oauth  # reaproveita APP_ID/SECRET — mesmo app Meta

API_URL = GRAPH_URL
API_VERSION = GRAPH_VERSION
CALLBACK_URL = os.environ.get("FACEBOOK_CALLBACK_URL")
# Meta descontinuou o produto clássico "Facebook Login" (scope= direto)
# pra apps novos — só "Login do Facebook para Empresas" (Business Login)
# fica disponível, e esse exige um config_id em vez de scope=. Sem isso
# o dialog OAuth retorna "Aplicativo inativo". config_id criado em
# Login do Facebook para Empresas > Configurações, com as permissões
# pages_show_list/pages_read_engagement/pages_manage_posts.
CONFIG_ID = os.environ.get("FACEBOOK_CONFIG_ID")


class FacebookOAuthError(Exception):
    pass


def get_user_auth_url(state: str) -> str:
    # `state` é ecoado pelo Meta de volta no /callback — usado pelo
    # router (api/routers/credentials.py) pra CSRF binding do
    # account-linking (evita que um atacante induza a vítima a linkar a
    # conta social DELE à conta da vítima).
    return (
        f"https://www.facebook.com/{API_VERSION}/dialog/oauth"
        f"?client_id={instagram_oauth.APP_ID}"
        f"&redirect_uri={quote(CALLBACK_URL or '', safe='')}"
        f"&config_id={CONFIG_ID}"
        "&response_type=code"
        f"&state={quote(state, safe='')}"
    )


async def _get_user_short_lived_token(code: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/{API_VERSION}/oauth/access_token",
            params={
                "client_id": instagram_oauth.APP_ID,
                "client_secret": instagram_oauth.SECRET,
                "redirect_uri": CALLBACK_URL,
                "code": code,
            },
        )
    if res.status_code not in (200, 201):
        raise FacebookOAuthError(
            f"Failed to Get User Short-Lived Access Token: {res.status_code} {res.text}"
        )
    return res.json()["access_token"]


async def _get_user_long_lived_token(short_lived_access_token: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/{API_VERSION}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": instagram_oauth.APP_ID,
                "client_secret": instagram_oauth.SECRET,
                "fb_exchange_token": short_lived_access_token,
            },
        )
    if res.status_code not in (200, 201):
        raise FacebookOAuthError(
            f"Failed to Get User Long-Lived Access Token: {res.status_code} {res.text}"
        )
    return res.json()["access_token"]


async def get_user_page(user_access_token: str) -> tuple[str, str, str]:
    """Retorna (page_id, page_name, page_access_token) da primeira Página
    que o usuário administra — ver limitação de múltiplas páginas na
    docstring do módulo. O access_token de cada item já vem escopado
    pra aquela Página específica (Graph API), não precisa de mais
    nenhuma troca de token."""
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{API_URL}/{API_VERSION}/me/accounts",
            params={
                "fields": "id,name,access_token",
                "access_token": user_access_token,
            },
        )
    if res.status_code not in (200, 201):
        raise FacebookOAuthError(
            f"Failed to Get Facebook Pages: {res.status_code} {res.text}"
        )
    pages = res.json().get("data", [])
    if not pages:
        raise FacebookOAuthError(
            "Nenhuma Página do Facebook encontrada para este usuário."
        )
    page = pages[0]
    return page["id"], page.get("name", ""), page["access_token"]


async def get_user_auth_page_token(code: str) -> tuple[str, str, str]:
    """Troca o code do callback por (page_id, page_name, page_access_token)
    da Página do usuário."""
    short_lived_token = await _get_user_short_lived_token(code)
    user_access_token = await _get_user_long_lived_token(short_lived_token)
    return await get_user_page(user_access_token)

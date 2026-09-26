"""
X (Twitter) API v2 — publicação e OAuth 2.0 Authorization Code + PKCE.

BLOQUEIO EXTERNO CONHECIDO (não resolvível por código, requer ação manual
de Rafa no X Developer Portal do app usado por cada usuário):
  1. O app precisa ter "User authentication settings" (OAuth 2.0)
     habilitado, com o redirect URI de X_CALLBACK_URL cadastrado.
  2. Dependendo do volume de posts, pode exigir tier pago (Free tier do
     X tem limite de escrita bem baixo).
Sem isso, `exchange_code_for_token`/`refresh_access_token` abaixo batem
na API real e recebem erro do lado do X — o código está completo e
correto pro fluxo documentado, só não é testável de ponta a ponta sem
essa configuração externa existir. Fato verificado na doc oficial:
POST /2/tweets exige contexto de usuário (OAuth 2.0 User Context com
escopo tweet.write, ou OAuth 1.0a) — Bearer Token app-only
(client_credentials, usado antes neste arquivo) não tem permissão para
postar em nome de uma conta, só para endpoints de leitura pública.

Diferente do Threads (app único da plataforma, credenciais em env): X
usa um app POR USUÁRIO — cada usuário cadastra seu próprio app_id/secret
do X Developer Portal (salvo em x_credentials via PUT /credentials/x).
Por isso client_id/client_secret aqui são sempre parâmetros, nunca env.
"""

import base64
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode

import requests
from shopee_bot.utils import retry_with_backoff

API_BASE = "https://api.twitter.com/2"
AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
CALLBACK_URL = os.environ.get("X_CALLBACK_URL")
DEFAULT_SCOPES = "tweet.read tweet.write users.read offline.access"


def _basic_auth_header(app_id, secret):
    credentials = base64.b64encode(f"{app_id}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def _bearer_token(app_id, secret, _cache={}):
    """Obtém Bearer Token via OAuth 2.0 Client Credentials.

    App-only: só serve para validar app_id/secret (validate_credentials)
    e endpoints de leitura pública. NÃO usar para postar (ver bloqueio
    externo no topo do arquivo).
    Cache por (app_id, secret) para não renovar a cada chamada."""
    key = (app_id, secret)
    if key in _cache and time.time() - _cache[key]["_t"] < 3300:
        return _cache[key]["token"]
    url = "https://api.twitter.com/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        **_basic_auth_header(app_id, secret),
    }
    body = {"grant_type": "client_credentials"}
    res = retry_with_backoff(
        requests.post, url, headers=headers, data=body,
        exceptions=(requests.exceptions.RequestException,),
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"X: falha ao obter Bearer Token (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    data = res.json()
    token = data.get("access_token")
    if not token:
        raise Exception(f"X: resposta inesperada ao obter Bearer Token: {data}")
    _cache[key] = {"token": token, "_t": time.time()}
    return token

def validate_credentials(app_id, secret):
    """Valida Bearer Token obtendo user me.
    Usa um request leve para confirmar que o app_id/secret funcionam
    (app-only) — não confirma permissão de postagem, que exige o fluxo
    de usuário abaixo."""
    token = _bearer_token(app_id, secret)
    headers = {"Authorization": f"Bearer {token}"}
    res = retry_with_backoff(
        requests.get, f"{API_BASE}/users/me", headers=headers,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code != 200:
        raise Exception(
            f"X: credenciais inválidas (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    data = res.json()
    if "data" not in data or "id" not in data["data"]:
        raise Exception(f"X: resposta inesperada ao validar credenciais: {data}")
    return data["data"]


###
# User AUTH — OAuth 2.0 Authorization Code + PKCE
# https://developer.x.com/en/docs/authentication/oauth-2-0/authorization-code
###
def generate_pkce_pair():
    """Gera (code_verifier, code_challenge) para o fluxo PKCE (S256)."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def get_user_auth_url(client_id, code_challenge, state, redirect_uri=None, scopes=DEFAULT_SCOPES):
    """Monta a URL de autorização do X para o usuário logar e conceder
    permissão de postagem. `client_id` é o app_id salvo pelo usuário em
    x_credentials (cada usuário usa seu próprio app do X Developer
    Portal)."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri or CALLBACK_URL,
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(client_id, client_secret, code, code_verifier, redirect_uri=None):
    """Troca o `code` do callback por access_token/refresh_token de usuário."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        **_basic_auth_header(client_id, client_secret),
    }
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or CALLBACK_URL,
        "code_verifier": code_verifier,
        "client_id": client_id,
    }
    res = retry_with_backoff(
        requests.post, TOKEN_URL, headers=headers, data=body,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"X: falha ao trocar code por token (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    return res.json()


def refresh_access_token(client_id, client_secret, refresh_token):
    """Renova o access_token de usuário a partir do refresh_token salvo
    (escopo offline.access, concedido por padrão em DEFAULT_SCOPES)."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        **_basic_auth_header(client_id, client_secret),
    }
    body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    res = retry_with_backoff(
        requests.post, TOKEN_URL, headers=headers, data=body,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"X: falha ao renovar token (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    return res.json()


###
# Publicação — exige access_token de USUÁRIO (ver bloqueio externo no
# topo do arquivo). Bearer app-only não funciona aqui.
###
def post_text(user_access_token, text, reply_to_id=None):
    """Posta um Tweet de texto puro em nome do usuário dono do token."""
    headers = {
        "Authorization": f"Bearer {user_access_token}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}
    if reply_to_id is not None:
        payload["reply"] = {"in_reply_to_tweet_id": str(reply_to_id)}
    res = retry_with_backoff(
        requests.post, f"{API_BASE}/tweets", headers=headers,
        json=payload, exceptions=(requests.exceptions.RequestException,),
        timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"X: falha ao publicar Tweet (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    data = res.json()
    return data.get("data", {})

def post_product(user_access_token, product):
    """Posta Tweet com link de afiliado de um produto Shopee.

    O link da Shopee já é transformado em card pelo X automaticamente.
    """
    commission_link = (
        product.get("commission_link")
        or product.get("original_link")
        or ""
    )
    name = product.get("name", "[produto]")
    commission = product.get("commission")
    price_min = product.get("price_min")
    price_max = product.get("price_max")

    text = (
        f"🔥 {name}\n"
        f"💰 Comissão: {commission}%\n"
    )
    if price_min is not None or price_max is not None:
        text += f"💲 Faixa: R$ {price_min} - R$ {price_max}\n"
    if commission_link:
        text += f"\n{commission_link}"
    return post_text(user_access_token, text)

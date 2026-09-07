import os
import json
import base64
import time
import requests
from shopee_bot.utils import retry_with_backoff

API_BASE = "https://api.twitter.com/2"

def _basic_auth_header(app_id, secret):
    credentials = base64.b64encode(f"{app_id}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}

def _bearer_token(app_id, secret, _cache={}):
    """Obtém Bearer Token via OAuth 2.0 Client Credentials.
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
    Usa um request leve para confirmar que o token funciona."""
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

def post_text(app_id, secret, text):
    """Posta um Tweet de texto puro."""
    token = _bearer_token(app_id, secret)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}
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

def post_product(app_id, secret, product):
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
    return post_text(app_id, secret, text)

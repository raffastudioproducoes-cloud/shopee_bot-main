"""OAuth de criadores Shopee Vídeo (Open Platform, não Affiliate GraphQL).

Contrato oficial: https://open.shopee.com/developer-guide/706
Para criadores afiliados, o consentimento usa ``auth_type=user``. O segredo
pertence à aplicação global e nunca é enviado ao navegador. A assinatura é
HMAC-SHA256 de partner_id + API path + timestamp, com partner_key.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx


LIVE_AUTH = "https://open.shopee.com.br/auth"
SANDBOX_AUTH = "https://open.test-stable.shopee.com.br/auth"
LIVE_API = "https://openplatform.shopee.com.br"
SANDBOX_API = "https://openplatform.sandbox.test-stable.shopee.sg"
TOKEN_PATH = "/api/v2/auth/token/get"
REFRESH_PATH = "/api/v2/auth/access_token/get"


class ShopeeVideoOAuthError(Exception):
    """Erro externo deliberadamente sem corpo HTTP, código ou credenciais."""


def authorization_url(partner_id: int, redirect_uri: str, state: str, *, sandbox: bool) -> str:
    if partner_id <= 0 or not redirect_uri.startswith("https://") or not state:
        raise ValueError("Configuração de OAuth Shopee Vídeo incompleta")
    return (SANDBOX_AUTH if sandbox else LIVE_AUTH) + "?" + urlencode({
        "partner_id": partner_id,
        "auth_type": "user",
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
    })


def signature(partner_id: int, partner_key: str, path: str, timestamp: int) -> str:
    signed = f"{partner_id}{path}{timestamp}"
    return hmac.new(partner_key.encode(), signed.encode(), hashlib.sha256).hexdigest()


async def _token_request(partner_id: int, partner_key: str, path: str, body: dict, *, sandbox: bool) -> dict:
    if path not in (TOKEN_PATH, REFRESH_PATH):
        raise ValueError("Endpoint OAuth não permitido")
    stamp = int(time.time())
    params = {
        "partner_id": partner_id, "timestamp": stamp,
        "sign": signature(partner_id, partner_key, path, stamp),
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(
                (SANDBOX_API if sandbox else LIVE_API) + path,
                params=params, json=body,
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ShopeeVideoOAuthError("Falha na comunicação OAuth com a Shopee") from exc
    if not isinstance(payload, dict) or payload.get("error"):
        raise ShopeeVideoOAuthError("A Shopee recusou a autorização de vídeo")
    if not payload.get("access_token") or not payload.get("refresh_token"):
        raise ShopeeVideoOAuthError("A Shopee não forneceu tokens de acesso válidos")
    return payload


async def exchange_code(partner_id: int, partner_key: str, code: str, *, sandbox: bool) -> dict:
    if not code or len(code) > 4096:
        raise ShopeeVideoOAuthError("Código de autorização inválido")
    result = await _token_request(partner_id, partner_key, TOKEN_PATH, {
        "code": code, "partner_id": partner_id,
    }, sandbox=sandbox)
    ids = result.get("user_id_list") or []
    if not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], int) or ids[0] <= 0:
        raise ShopeeVideoOAuthError("Autorização não identificou um criador Shopee único")
    return result


async def refresh_token(partner_id: int, partner_key: str, user_id: int, refresh: str, *, sandbox: bool) -> dict:
    if user_id <= 0 or not refresh:
        raise ShopeeVideoOAuthError("Autorização Shopee Vídeo incompleta")
    return await _token_request(partner_id, partner_key, REFRESH_PATH, {
        "refresh_token": refresh, "partner_id": partner_id, "user_id": user_id,
    }, sandbox=sandbox)

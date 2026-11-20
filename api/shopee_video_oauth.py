"""OAuth de criadores Shopee Vídeo (Open Platform, não Affiliate GraphQL).

Contrato oficial: https://open.shopee.com/developer-guide/706
Para criadores afiliados, o consentimento usa ``auth_type=user``. O segredo
pertence à aplicação global e nunca é enviado ao navegador. A assinatura é
HMAC-SHA256 de partner_id + API path + timestamp, com partner_key.
O host das chamadas de token é o mesmo do cliente (apis/shopee_video_host.py);
só a página de consentimento usa open.shopee.com.br.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import httpx

from apis.shopee_video_host import api_base_url

logger = logging.getLogger(__name__)


LIVE_AUTH = "https://open.shopee.com.br/auth"
SANDBOX_AUTH = "https://open.test-stable.shopee.com/auth"  # o host .com.br do sandbox não existe (DNS)
TOKEN_PATH = "/api/v2/auth/token/get"
REFRESH_PATH = "/api/v2/auth/access_token/get"


class ShopeeVideoOAuthError(Exception):
    """Erro externo deliberadamente sem corpo HTTP, código ou credenciais."""


class ShopeeVideoRefreshRejected(ShopeeVideoOAuthError):
    """A Shopee recusou o refresh_token (usado, expirado ou revogado): reconectar."""


def api_host(*, sandbox: bool) -> str:
    return api_base_url(sandbox=sandbox)


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


def _request_parts(partner_id: int, partner_key: str, path: str, *, sandbox: bool) -> tuple[str, dict]:
    if path not in (TOKEN_PATH, REFRESH_PATH):
        raise ValueError("Endpoint OAuth não permitido")
    stamp = int(time.time())
    params = {
        "partner_id": partner_id, "timestamp": stamp,
        "sign": signature(partner_id, partner_key, path, stamp),
    }
    return api_host(sandbox=sandbox) + path, params


# Erros da Shopee que indicam instabilidade, não token inválido.
TRANSIENT_ERRORS = frozenset({"error_server", "error_inner", "error_busy", "error_network"})


def _payload(response) -> object:
    """Lê o corpo mesmo em HTTP 4xx: a Shopee manda o motivo no JSON."""
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and payload.get("error"):
        return payload
    response.raise_for_status()
    return payload


def _log_shopee_error(payload: object, path: str) -> None:
    """Registra só o código, a mensagem e o request_id da Shopee (nunca tokens), para diagnóstico."""
    if not isinstance(payload, dict):
        logger.warning("Shopee Vídeo OAuth: resposta inesperada em %s", path)
        return
    logger.warning("Shopee Vídeo OAuth recusado em %s: error=%s message=%s request_id=%s", path,
                   str(payload.get("error"))[:60], str(payload.get("message"))[:200],
                   str(payload.get("request_id"))[:64])


def _checked(payload: object, path: str) -> dict:
    if isinstance(payload, dict) and str(payload.get("error")) in TRANSIENT_ERRORS:
        raise ShopeeVideoOAuthError("Shopee indisponível no momento; tente de novo")
    if not isinstance(payload, dict) or payload.get("error"):
        _log_shopee_error(payload, path)
        if path == REFRESH_PATH:
            raise ShopeeVideoRefreshRejected("A Shopee recusou a renovação do acesso de vídeo")
        raise ShopeeVideoOAuthError("A Shopee recusou a autorização de vídeo")
    if not payload.get("access_token") or not payload.get("refresh_token"):
        raise ShopeeVideoOAuthError("A Shopee não forneceu tokens de acesso válidos")
    return payload


async def _token_request(partner_id: int, partner_key: str, path: str, body: dict, *, sandbox: bool) -> dict:
    url, params = _request_parts(partner_id, partner_key, path, sandbox=sandbox)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            payload = _payload(await client.post(url, params=params, json=body))
    except (httpx.HTTPError, ValueError) as exc:
        raise ShopeeVideoOAuthError("Falha na comunicação OAuth com a Shopee") from exc
    return _checked(payload, path)


def _token_request_sync(partner_id: int, partner_key: str, path: str, body: dict, *, sandbox: bool) -> dict:
    """Versão síncrona para o scheduler (gevent), onde asyncio.run não é seguro."""
    url, params = _request_parts(partner_id, partner_key, path, sandbox=sandbox)
    try:
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            payload = _payload(client.post(url, params=params, json=body))
    except (httpx.HTTPError, ValueError) as exc:
        raise ShopeeVideoOAuthError("Falha na comunicação OAuth com a Shopee") from exc
    return _checked(payload, path)


async def exchange_code(partner_id: int, partner_key: str, code: str, *, sandbox: bool) -> dict:
    if not code or len(code) > 4096:
        raise ShopeeVideoOAuthError("Código de autorização inválido")
    result = await _token_request(partner_id, partner_key, TOKEN_PATH, {
        "code": code, "partner_id": partner_id,
    }, sandbox=sandbox)
    # Afiliado (auth_type=user): a doc diz que a troca devolve só o user_id; aceitamos tanto
    # `user_id` quanto `user_id_list` com um único item e normalizamos para `user_id_list`.
    ids = result.get("user_id_list") or ([result["user_id"]] if result.get("user_id") else [])
    if not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], int) or ids[0] <= 0:
        logger.warning("Shopee Vídeo OAuth: resposta sem um user_id único (campos: %s)", sorted(result.keys()))
        raise ShopeeVideoOAuthError("Autorização não identificou um criador Shopee único")
    return {**result, "user_id_list": ids}


def refresh_token_sync(partner_id: int, partner_key: str, user_id: int, refresh: str, *, sandbox: bool) -> dict:
    """Troca o refresh_token (uso único) por um par novo; o chamador grava os dois."""
    if user_id <= 0 or not refresh:
        raise ShopeeVideoOAuthError("Autorização Shopee Vídeo incompleta")
    body = {"refresh_token": refresh, "partner_id": partner_id, "user_id": user_id}
    return _token_request_sync(partner_id, partner_key, REFRESH_PATH, body, sandbox=sandbox)

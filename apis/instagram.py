"""
Instagram API via Meta Graph API (Facebook side).

Publicação via Graph API usando App Access Token (client_credentials).
Fluxo:
  1. Validate credentials: App Access Token + verificar user Instagram (se
     tiver user_access_token salvo) ou só App Token.
  2. Publicar: criar container de mídia de texto (Instagram suporta texto
     como 'TEXT' no Media Container) e publicar com polling.

Notas:
  - Instagram requer usuário/autorização para publicar via Graph API.
  - App Access Token só funciona para obter endpoints públicos e para
    publicar se o app estiver autorizado para o usuário Instagram via
    OAuth (user_access_token).
  - A tabela instagram_credentials só tem app_id (IG App ID) e secret (IG App
    Secret) → não há user_access_token salvo ainda.
  - Para publicar TEXTO sem imagem/video, Instagram aceita media_type TEXT
    desde que o usuário tenha autorização.
  - Se a conta for Business/Creator com Instagram Graph API habilitada,
    publicação via Graph API funciona com o token de usuário longo.

Recomendação do README:
  - Hoje o wrapper implementa validação e postagem básica (TEXT),
    mas a publicação só funcionará com user_access_token adicional.
  - Se a conta não tiver autorização, post_text levanta NotImplementedError
    com orientação de como obter o token.
"""

import os
import time
import json
import requests
from shopee_bot.utils import retry_with_backoff

API_BASE = "https://graph.facebook.com/v18.0"

# Tokens: app_id = Instagram App ID, secret = Instagram App Secret.
# user_access_token salvo em env ou em coluna extra da tabela futura.

def _app_access_token(app_id, secret, _cache={}):
    key = (app_id, secret)
    if key in _cache and time.time() - _cache[key]["_t"] < 5400:
        return _cache[key]["token"]
    url = f"{API_BASE}/oauth/access_token"
    params = {
        "client_id": app_id,
        "client_secret": secret,
        "grant_type": "client_credentials",
    }
    res = retry_with_backoff(
        requests.get, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code != 200:
        raise Exception(
            f"Instagram: falha ao obter App Access Token "
            f"(status {res.status_code}): {res.text[:300]}"
        )
    data = res.json()
    token = data.get("access_token")
    if not token:
        raise Exception(f"Instagram: resposta inesperada: {data}")
    _cache[key] = {"token": token, "_t": time.time()}
    return token

def _user_id_from_token(user_access_token, _cache={}):
    """Obtém o ID da conta Instagram a partir do user_access_token."""
    url = f"{API_BASE}/me"
    params = {"access_token": user_access_token, "fields": "id"}
    res = retry_with_backoff(
        requests.get, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code != 200:
        raise Exception(
            f"Instagram: falha ao obter usuário (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    data = res.json()
    return data.get("id")

def validate_credentials(app_id, secret, user_access_token=None):
    """Valida credenciais Instagram.

    Se user_access_token fornecido, testa obter o usuário e a conta.
    Se não, só valida App Token (só app-level).
    """
    app_token = _app_access_token(app_id, secret)
    url_app = f"{API_BASE}/me"
    params_app = {"access_token": app_token, "fields": "id"}
    res_app = retry_with_backoff(
        requests.get, url_app, params=params_app,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res_app.status_code != 200:
        raise Exception(
            f"Instagram: App Token inválido (status {res_app.status_code}): "
            f"{res_app.text[:300]}"
        )
    app_data = res_app.json()
    result = {"app": app_data.get("id")}
    if user_access_token:
        user_id = _user_id_from_token(user_access_token)
        result["user_id"] = user_id
    return result

def _create_text_media_container(ig_user_id, user_access_token, text):
    """Cria container de mídia de TEXTO para publicação no Instagram."""
    url = f"{API_BASE}/{ig_user_id}/media"
    params = {
        "access_token": user_access_token,
        "media_type": "TEXT",
        "caption": text,
    }
    res = retry_with_backoff(
        requests.post, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"Instagram: falha ao criar container de texto "
            f"(status {res.status_code}): {res.text[:300]}"
        )
    data = res.json()
    creation_id = data.get("id")
    if not creation_id:
        raise Exception(f"Instagram: resposta inesperada ao criar container: {data}")
    return creation_id

def _poll_media_container(user_access_token, creation_id):
    """Polla até o container de mídia estar READY."""
    while True:
        url = f"{API_BASE}/{creation_id}"
        params = {
            "access_token": user_access_token,
            "fields": "status_code",
        }
        res = retry_with_backoff(
            requests.get, url, params=params,
            exceptions=(requests.exceptions.RequestException,),
            timeout=15,
        )
        if res.status_code != 200:
            raise Exception(
                f"Instagram: falha ao consultar container "
                f"(status {res.status_code}): {res.text[:300]}"
            )
        data = res.json()
        status_code = data.get("status_code")
        if status_code == "READY":
            return True
        if status_code in ("ERROR",):
            raise Exception(f"Instagram: container em estado {status_code}")
        time.sleep(1)

def _publish_media_container(ig_user_id, user_access_token, creation_id):
    """Publica o container de mídia no Instagram."""
    url = f"{API_BASE}/{ig_user_id}/media_publish"
    params = {
        "creation_id": creation_id,
        "access_token": user_access_token,
    }
    res = retry_with_backoff(
        requests.post, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"Instagram: falha ao publicar "
            f"(status {res.status_code}): {res.text[:300]}"
        )
    data = res.json()
    media_id = data.get("id")
    if not media_id:
        raise Exception(f"Instagram: resposta inesperada ao publicar: {data}")
    return media_id

def post_text(app_id, secret, user_access_token, text):
    """Posta um texto (caption) no Instagram via Graph API.

    Pré-requisitos:
      - user_access_token com permissões instagram_basic e
        instagram_content_publish.
      - Conta Business ou Creator com Instagram Graph API habilitada.
    """
    if not user_access_token:
        raise NotImplementedError(
            "Instagram: user_access_token é obrigatório para publicar. "
            "Implemente OAuth ou salve o token na tabela/credential. "
            "Ver: https://developers.facebook.com/docs/instagram-api"
        )
    app_token = _app_access_token(app_id, secret)
    # Obtém o usuário Instagram conectado
    user_id = _user_id_from_token(user_access_token)
    # Obtém o Instagram Business Account (node)
    url_ig = f"{API_BASE}/{user_id}"
    params_ig = {
        "access_token": user_access_token,
        "fields": "instagram_business_account{id,username}",
    }
    res_ig = retry_with_backoff(
        requests.get, url_ig, params=params_ig,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res_ig.status_code != 200:
        raise Exception(
            f"Instagram: falha ao obter conta business "
            f"(status {res_ig.status_code}): {res_ig.text[:300]}"
        )
    data_ig = res_ig.json()
    ig_business = data_ig.get("instagram_business_account")
    if not ig_business or not ig_business.get("id"):
        raise NotImplementedError(
            "Instagram: conta do usuário não está vinculada a uma conta "
            "Instagram Business/Creator (instagram_business_account ausente). "
            "Conecte uma conta Business ou use um user token com permissões."
        )
    ig_user_id = ig_business["id"]

    creation_id = _create_text_media_container(
        ig_user_id, user_access_token, text
    )
    _poll_media_container(user_access_token, creation_id)
    media_id = _publish_media_container(ig_user_id, user_access_token, creation_id)
    return media_id

def post_product(app_id, secret, user_access_token, product):
    """Posta texto com link de afiliado de produto Shopee no Instagram."""
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
    )
    if commission is not None:
        text += f"Comissão: {commission}%\n"
    if price_min is not None or price_max is not None:
        text += f"Faixa: R$ {price_min} a R$ {price_max}\n"
    if commission_link:
        text += f"\n{commission_link}"

    return post_text(app_id, secret, user_access_token, text)

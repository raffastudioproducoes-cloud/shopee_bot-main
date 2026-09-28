"""
Facebook API wrapper (Meta Graph API).

BLOQUEIO EXTERNO CONHECIDO — App Review da Meta:
Publicar de fato em `POST /{page-id}/feed` exige a permissão
`pages_manage_posts`, que só fica disponível em produção depois que o
App Review da Meta aprova o app para essa permissão. Até isso acontecer,
`post_text`/`post_product` só funcionam em páginas onde o usuário (ou o
app registrado no Meta Developer Console) já é Admin/Tester — ou seja,
páginas fora do modo de desenvolvimento do app vão falhar com erro de
permissão da Graph API. Isso é uma limitação da Meta, não deste código;
não há workaround client-side.
"""

import os
import time
import json
import requests
from shopee_bot.utils import retry_with_backoff

API_BASE = "https://graph.facebook.com/v18.0"

def _app_access_token(app_id, secret, _cache={}):
    """Obtém App Access Token via OAuth client_credentials.
    Cache por (app_id, secret)."""
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
            f"Facebook: falha ao obter App Access Token (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    data = res.json()
    token = data.get("access_token")
    if not token:
        raise Exception(f"Facebook: resposta inesperada: {data}")
    _cache[key] = {"token": token, "_t": time.time()}
    return token

def _page_access_token(app_id, secret, page_id, _cache={}):
    """Obtém Page Access Token via App Token + /me/accounts."""
    key = (app_id, secret, page_id)
    if key in _cache and time.time() - _cache[key]["_t"] < 5400:
        return _cache[key]["token"]
    app_token = _app_access_token(app_id, secret)
    url = f"{API_BASE}/me/accounts"
    params = {"access_token": app_token}
    res = retry_with_backoff(
        requests.get, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code != 200:
        raise Exception(
            f"Facebook: falha ao listar páginas (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    data = res.json()
    pages = data.get("data", [])
    target = None
    for page in pages:
        if str(page.get("id")) == str(page_id):
            target = page.get("access_token")
            break
    if not target:
        raise Exception(
            f"Facebook: página '{page_id}' não encontrada nas páginas do app "
            f"(disponíveis: {[p.get('id') for p in pages]})"
        )
    _cache[key] = {"token": target, "_t": time.time()}
    return target

def _pages_list(app_id, secret):
    """Lista páginas/perfis gerenciáveis pelo app token."""
    app_token = _app_access_token(app_id, secret)
    url = f"{API_BASE}/me/accounts"
    params = {"access_token": app_token}
    res = retry_with_backoff(
        requests.get, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code != 200:
        raise Exception(
            f"Facebook: falha ao listar páginas (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    return res.json().get("data", [])

def validate_credentials(app_id, secret, page_id=None):
    """Valida credenciais Facebook App.

    Se page_id fornecido, valida App Token + Page Access Token.
    Se não, só valida App Token (lista páginas disponíveis).
    """
    app_token = _app_access_token(app_id, secret)
    # validação do app
    url = f"{API_BASE}/me"
    params = {"access_token": app_token, "fields": "id,name"}
    res = retry_with_backoff(
        requests.get, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code != 200:
        raise Exception(
            f"Facebook: credenciais inválidas (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    me = res.json()
    if page_id:
        # valida page token
        page_token = _page_access_token(app_id, secret, page_id)
        url_page = f"{API_BASE}/{page_id}"
        params_page = {"access_token": page_token, "fields": "id,name"}
        res_page = retry_with_backoff(
            requests.get, url_page, params=params_page,
            exceptions=(requests.exceptions.RequestException,),
            timeout=15,
        )
        if res_page.status_code != 200:
            raise Exception(
                f"Facebook: página inválida (status {res_page.status_code}): "
                f"{res_page.text[:300]}"
            )
        page_data = res_page.json()
        return {"app": me.get("id"), "page": page_data}
    return {"app": me.get("id"), "pages": _pages_list(app_id, secret)}

def post_text(app_id, secret, page_id, text):
    """Posta texto na Timeline de uma página do Facebook.

    page_id é obrigatório — a tabela não armazena page ID hoje,
    mas a validação retorna as páginas disponíveis para o app.
    """
    if not page_id:
        raise Exception(
            "Facebook: page_id é obrigatório para publicação. "
            "Obtém disponíveis via validate_credentials (sem page_id) ou "
            "atualiza o schema para salvar page_id."
        )
    page_token = _page_access_token(app_id, secret, page_id)
    url = f"{API_BASE}/{page_id}/feed"
    params = {
        "message": text,
        "access_token": page_token,
    }
    res = retry_with_backoff(
        requests.post, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"Facebook: falha ao publicar (status {res.status_code}): "
            f"{res.text[:300]}"
        )
    return res.json()

def validate_page_access_token(page_access_token, page_id):
    """Valida um Page Access Token obtido via OAuth do usuário (Login do
    Facebook, ver api/facebook_oauth.py) — token já escopado pra Página
    certa, não precisa derivar via App Token. Complementa
    validate_credentials (fluxo antigo per-user, app_id/secret)."""
    if not page_id:
        raise Exception("Facebook: nenhuma Página vinculada a esta conexão.")
    url = f"{API_BASE}/{page_id}"
    params = {"access_token": page_access_token, "fields": "id,name"}
    res = retry_with_backoff(
        requests.get, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )
    if res.status_code != 200:
        raise Exception(
            f"Facebook: token da página inválido (status {res.status_code}): {res.text[:300]}"
        )
    return res.json()

def post_text_as_page(page_access_token, page_id, text):
    """Publica usando um Page Access Token já resolvido via OAuth do
    usuário (api/facebook_oauth.py::get_user_page) — não deriva token
    via App Token, então funciona pra Páginas de qualquer usuário que
    autorizar, não só as que o app do Rafa administra."""
    url = f"{API_BASE}/{page_id}/feed"
    params = {
        "message": text,
        "access_token": page_access_token,
    }
    res = retry_with_backoff(
        requests.post, url, params=params,
        exceptions=(requests.exceptions.RequestException,),
        timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"Facebook: falha ao publicar (status {res.status_code}): {res.text[:300]}"
        )
    return res.json()

def post_product_as_page(page_access_token, page_id, product):
    """Mesmo texto de post_product, mas publicando com Page Access Token
    (fluxo OAuth novo) em vez de app_id/secret (fluxo antigo per-user)."""
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
        text += f"Faixa de preço: R$ {price_min} a R$ {price_max}\n"
    if commission_link:
        text += f"\n{commission_link}"

    return post_text_as_page(page_access_token, page_id, text)

def post_product(app_id, secret, page_id, product):
    """Posta texto com link de afiliado de um produto Shopee na página do Facebook.

    A página do Facebook renderiza o link como card automaticamente.
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
    )
    if commission is not None:
        text += f"Comissão: {commission}%\n"
    if price_min is not None or price_max is not None:
        text += f"Faixa de preço: R$ {price_min} a R$ {price_max}\n"
    if commission_link:
        text += f"\n{commission_link}"

    return post_text(app_id, secret, page_id, text)

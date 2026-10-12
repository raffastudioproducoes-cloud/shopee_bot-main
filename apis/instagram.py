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
  - A tabela instagram_credentials tem user_access_token e ig_user_id
    (colunas adicionadas na migration 024), preenchidas pelo fluxo OAuth
    de Facebook Login for Business em api/instagram_oauth.py — ver
    scheduler/bot_post_instagram.py pra onde esses valores são lidos e
    passados pra post_text/post_product.
  - Para publicar TEXTO sem imagem/video, Instagram aceita media_type TEXT
    desde que o usuário tenha autorização.
  - Se a conta for Business/Creator com Instagram Graph API habilitada,
    publicação via Graph API funciona com o token de usuário longo.

BLOQUEIO EXTERNO (App Review da Meta):
  - Publicar de verdade (media_publish) exige a permissão
    instagram_content_publish aprovada em App Review — processo manual e
    separado, feito no mesmo Meta Developer Console do app. Sem essa
    aprovação, a Graph API só publica para usuários cadastrados como
    tester do app (Roles > Testers no console do app).
  - Isso é bloqueio de processo externo (Meta), não desta implementação:
    o código abaixo funciona normalmente pra quem é tester; para os
    demais usuários, media_publish retorna erro de permissão até o App
    Review ser aprovado. Não há workaround de código pra isso.

Recomendação do README:
  - Hoje o wrapper implementa validação e postagem básica (TEXT),
    mas a publicação só funcionará com user_access_token adicional.
  - Se a conta não tiver autorização, post_text levanta NotImplementedError
    com orientação de como obter o token.
"""

import time
import requests
from shopee_bot.utils import ConnectionTestError, retry_with_backoff

# Mesma versão do OAuth (api/instagram_oauth.py::API_VERSION).
API_BASE = "https://graph.facebook.com/v19.0"

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

def _graph_get(path, user_access_token, fields):
    return retry_with_backoff(
        requests.get, f"{API_BASE}/{path}",
        params={"access_token": user_access_token, "fields": fields},
        exceptions=(requests.exceptions.RequestException,),
        timeout=15,
    )


def _raise_graph_error(res, what):
    """Traduz erro da Graph API sem ecoar o corpo (pode citar o token)."""
    try:
        code = ((res.json() or {}).get("error") or {}).get("code")
    except ValueError:
        code = None
    if code == 190:
        raise ConnectionTestError(
            "Token do Instagram/Facebook expirado ou revogado — reconecte"
        )
    if code in (10, 200, 283):
        raise ConnectionTestError(
            "Permissões insuficientes no token do Instagram — reconecte "
            "aceitando todas as permissões"
        )
    raise ConnectionTestError(f"Instagram: falha ao {what} (status {res.status_code})")


def validate_user_token(user_access_token, ig_user_id=None):
    """Valida o token do USUÁRIO (Facebook Login for Business), não o app.

    App access token não resolve /me. Confere /me com o token do usuário e
    a conta Instagram Business: a salva (ig_user_id) ou, se faltar, alguma
    Página do usuário com instagram_business_account. Levanta
    ConnectionTestError (mensagem sem token)."""
    res = _graph_get("me", user_access_token, "id")
    if res.status_code != 200:
        _raise_graph_error(res, "validar o token")
    if ig_user_id:
        res = _graph_get(ig_user_id, user_access_token, "id,username")
        if res.status_code != 200:
            _raise_graph_error(res, "acessar a conta Instagram vinculada")
        return {"ig_user_id": ig_user_id}
    res = _graph_get("me/accounts", user_access_token, "id,instagram_business_account")
    if res.status_code != 200:
        _raise_graph_error(res, "listar as Páginas")
    for page in (res.json() or {}).get("data", []):
        account = page.get("instagram_business_account") or {}
        if account.get("id"):
            return {"ig_user_id": account["id"]}
    raise ConnectionTestError(
        "Nenhuma Página com conta Instagram Business vinculada — vincule e reconecte"
    )


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

def _create_image_media_container(ig_user_id, user_access_token, image_url, caption):
    """Cria um container IMAGE a partir de URL pública para a Graph API."""
    url = f"{API_BASE}/{ig_user_id}/media"
    params = {"access_token": user_access_token, "image_url": image_url, "caption": caption}
    res = retry_with_backoff(
        requests.post, url, params=params,
        exceptions=(requests.exceptions.RequestException,), timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(
            f"Instagram: falha ao criar container de imagem (status {res.status_code}): {res.text[:300]}"
        )
    creation_id = (res.json() or {}).get("id")
    if not creation_id:
        raise Exception("Instagram: resposta inesperada ao criar container de imagem")
    return creation_id


IMAGE_POLL_ATTEMPTS = 60    # ~1 min
VIDEO_POLL_ATTEMPTS = 300   # ~5 min; vídeo/Reels demora a processar


def _poll_media_container(user_access_token, creation_id, attempts=IMAGE_POLL_ATTEMPTS):
    """Espera o container ficar FINISHED (status_code da Graph API:
    IN_PROGRESS, FINISHED, ERROR, EXPIRED, PUBLISHED). Falha em ERROR/EXPIRED
    e desiste ao fim das tentativas, em vez de travar o job."""
    for _ in range(attempts):
        res = retry_with_backoff(
            requests.get, f"{API_BASE}/{creation_id}",
            params={"access_token": user_access_token, "fields": "status_code"},
            exceptions=(requests.exceptions.RequestException,),
            timeout=15,
        )
        if res.status_code != 200:
            raise Exception(
                f"Instagram: falha ao consultar container "
                f"(status {res.status_code}): {res.text[:300]}"
            )
        status_code = res.json().get("status_code")
        if status_code == "FINISHED":
            return True
        if status_code in ("ERROR", "EXPIRED"):
            raise Exception(f"Instagram: container em estado {status_code}")
        time.sleep(1)
    raise Exception("Instagram: tempo esgotado esperando o container ficar pronto")

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

def _resolve_ig_user_id(user_access_token, ig_user_id=None):
    """Retorna o ig_user_id a usar: o salvo na credencial (vindo do OAuth
    de Facebook Login for Business, ver api/instagram_oauth.py), ou, se
    não fornecido, resolve na hora via /me + instagram_business_account
    (fallback pra credenciais antigas sem a coluna preenchida)."""
    if ig_user_id:
        return ig_user_id

    user_id = _user_id_from_token(user_access_token)
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
    return ig_business["id"]

def post_text(app_id, secret, user_access_token, text, ig_user_id=None):
    """Posta um texto (caption) no Instagram via Graph API.

    Pré-requisitos:
      - user_access_token com permissões instagram_basic e
        instagram_content_publish.
      - Conta Business ou Creator com Instagram Graph API habilitada.
      - ig_user_id: id da conta Instagram Business/Creator, salvo na
        credencial pelo fluxo OAuth. Se omitido, é resolvido na hora
        (fallback, mais lento — 1 chamada extra à Graph API).
    """
    if not user_access_token:
        raise NotImplementedError(
            "Instagram: user_access_token é obrigatório para publicar. "
            "Implemente OAuth ou salve o token na tabela/credential. "
            "Ver: https://developers.facebook.com/docs/instagram-api"
        )
    # app_token não é usado pra publicar (a Graph API usa o
    # user_access_token pros endpoints de media/media_publish), só
    # validado aqui pra falhar cedo se app_id/secret estiverem errados.
    _app_access_token(app_id, secret)
    ig_user_id = _resolve_ig_user_id(user_access_token, ig_user_id)

    creation_id = _create_text_media_container(
        ig_user_id, user_access_token, text
    )
    _poll_media_container(user_access_token, creation_id)
    media_id = _publish_media_container(ig_user_id, user_access_token, creation_id)
    return media_id

def post_product(app_id, secret, user_access_token, product, ig_user_id=None):
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

    return post_text(app_id, secret, user_access_token, text, ig_user_id)


def post_image(app_id, secret, user_access_token, image_url, caption, ig_user_id=None):
    """Publica imagem por URL pública e espera o container ficar pronto."""
    if not user_access_token:
        raise NotImplementedError("Instagram: user_access_token é obrigatório para publicar.")
    _app_access_token(app_id, secret)
    ig_user_id = _resolve_ig_user_id(user_access_token, ig_user_id)
    creation_id = _create_image_media_container(
        ig_user_id, user_access_token, image_url, caption
    )
    _poll_media_container(user_access_token, creation_id)
    return _publish_media_container(ig_user_id, user_access_token, creation_id)

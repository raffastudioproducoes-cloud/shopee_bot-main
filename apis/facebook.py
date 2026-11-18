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

import json
import time
from urllib.parse import urlsplit

import requests
from shopee_bot.utils import mark_not_published, retry_with_backoff
from shopee_bot.apis.meta_version import GRAPH_BASE

API_BASE = GRAPH_BASE

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

def post_photo_as_page(page_access_token, page_id, image_url, caption):
    """Publica uma foto por URL pública usando o Page Access Token OAuth."""
    url = f"{API_BASE}/{page_id}/photos"
    params = {"url": image_url, "caption": caption, "access_token": page_access_token}
    res = retry_with_backoff(
        requests.post, url, params=params,
        exceptions=(requests.exceptions.RequestException,), timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(f"Facebook: falha ao publicar imagem (status {res.status_code}): {res.text[:300]}")
    return res.json()


def post_album_as_page(page_access_token, page_id, image_urls, caption):
    """Publica várias fotos num único post: cada foto sobe sem publicar
    (`published=false`) e o post do feed anexa todas via `attached_media`.
    Se alguma foto falhar nada vai ao feed (fotos não publicadas ficam
    invisíveis)."""
    photo_ids = []
    for index, image_url in enumerate(image_urls, start=1):
        res = retry_with_backoff(
            requests.post, f"{API_BASE}/{page_id}/photos",
            params={"url": image_url, "published": "false", "access_token": page_access_token},
            exceptions=(requests.exceptions.RequestException,), timeout=30,
        )
        photo_id = (res.json() or {}).get("id") if res.status_code in (200, 201) else None
        if not photo_id:
            raise Exception(f"Facebook: falha ao enviar imagem {index} do álbum (status {res.status_code})")
        photo_ids.append(photo_id)
    params = {"message": caption, "access_token": page_access_token}
    for index, photo_id in enumerate(photo_ids):
        params[f"attached_media[{index}]"] = json.dumps({"media_fbid": photo_id})
    res = retry_with_backoff(
        requests.post, f"{API_BASE}/{page_id}/feed", params=params,
        exceptions=(requests.exceptions.RequestException,), timeout=30,
    )
    if res.status_code not in (200, 201):
        raise Exception(f"Facebook: falha ao publicar álbum (status {res.status_code}): {res.text[:300]}")
    return res.json()


def post_video_as_page(page_access_token, page_id, video_url, caption):
    """Publica vídeo por URL (`file_url`) em /{page}/videos. O Facebook baixa
    e processa depois; a resposta traz só o id do vídeo."""
    res = retry_with_backoff(
        requests.post, f"{API_BASE}/{page_id}/videos",
        params={"file_url": video_url, "description": caption, "access_token": page_access_token},
        exceptions=(requests.exceptions.RequestException,), timeout=60,
    )
    if res.status_code not in (200, 201):
        raise Exception(f"Facebook: falha ao publicar vídeo (status {res.status_code})")
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


# --- Reels de Página -------------------------------------------------------
# Doc oficial conferida em 18/11/2026 (página com exemplos em v27.0; o app usa a
# versão de meta_version.py): developers.facebook.com/docs/video-api/guides/reels-publishing
#   1. POST /{page-id}/video_reels upload_phase=start  -> video_id + upload_url
#   2. POST upload_url (rupload.facebook.com) com headers Authorization: OAuth <token>
#      e file_url: <URL pública>  -> {"success": true}
#   3. POST /{page-id}/video_reels upload_phase=finish, video_id, video_state=PUBLISHED,
#      description. A tabela de parâmetros diz enum{start,finish} mas também cita
#      "complete"; os exemplos de código usam `finish`: usamos `finish` e só tentamos
#      `complete` se a Meta recusar o valor (code 100).
#   4. GET /{video-id}?fields=status até publishing_phase.publish_status = published.
# Requisitos: MP4 (H.264/H.265), 9:16, mínimo 540x960, 3 a 90 s, 24-60 fps.
# Limite: 30 Reels publicados via API por Página em 24 h móveis (a Meta pede que o app
# também controle; ver scheduler/bot_post_facebook.py). Token de Página de quem pode
# executar a tarefa CREATE_CONTENT; permissões pages_show_list, pages_read_engagement e
# pages_manage_posts (as mesmas já usadas para publicar no feed).
REELS_MIN_SECONDS, REELS_MAX_SECONDS = 3, 90
REELS_MIN_WIDTH, REELS_MIN_HEIGHT = 540, 960
REELS_PER_PAGE_24H = 30
REELS_POLL_SECONDS = 300  # ~5 min, como o Instagram
REELS_POLL_INTERVAL = 5
REELS_UPLOAD_HOST = "rupload.facebook.com"
_REELS_FAILED_VIDEO_STATES = {"error", "upload_failed", "expired"}


def reel_requirements_error(file_name, info):
    """Mensagem (PT-BR) se o vídeo não serve para Reels, antes de qualquer chamada.

    `info` = {"width", "height", "duration"} lido do MP4; None = não deu para ler e a
    Meta valida no processamento."""
    if (file_name or "").rsplit(".", 1)[-1].lower() != "mp4":
        return "Facebook Reels: o vídeo precisa ser MP4."
    if not info:
        return None
    width, height, duration = info["width"], info["height"], info["duration"]
    if not REELS_MIN_SECONDS <= duration <= REELS_MAX_SECONDS:
        return (f"Facebook Reels: o vídeo precisa ter de {REELS_MIN_SECONDS} a {REELS_MAX_SECONDS} s "
                f"(o seu tem {round(duration)} s).")
    if width > height:
        return f"Facebook Reels: o vídeo precisa ser vertical 9:16 (o seu é {width}×{height})."
    if width < REELS_MIN_WIDTH or height < REELS_MIN_HEIGHT:
        return (f"Facebook Reels: resolução mínima {REELS_MIN_WIDTH}×{REELS_MIN_HEIGHT} "
                f"(o seu é {width}×{height}).")
    return None


def reel_aspect_warning(info):
    """Vertical mas fora de 9:16: publica, só avisa (a Meta recomenda 9:16)."""
    if info and info["height"] and abs(info["width"] / info["height"] - 9 / 16) > 0.01:
        return f"Facebook Reels: vídeo {info['width']}×{info['height']} não é 9:16; pode aparecer com bordas."
    return None


def _graph_code(res):
    try:
        code = ((res.json() or {}).get("error") or {}).get("code")
    except (ValueError, AttributeError):
        return None
    return code if isinstance(code, int) else None


def _json(res):
    try:
        body = res.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _start_reel_upload(page_access_token, page_id):
    res = retry_with_backoff(
        requests.post, f"{API_BASE}/{page_id}/video_reels",
        params={"upload_phase": "start", "access_token": page_access_token},
        exceptions=(requests.exceptions.RequestException,), timeout=30,
    )
    body = _json(res) if res.status_code in (200, 201) else {}
    video_id = body.get("video_id")
    if not video_id:
        raise Exception(
            f"Facebook Reels: falha ao iniciar o envio (status {res.status_code}, código {_graph_code(res)})"
        )
    version = API_BASE.rsplit("/", 1)[-1]
    upload_url = body.get("upload_url") or f"https://{REELS_UPLOAD_HOST}/video-upload/{version}/{video_id}"
    # O token vai no header: só para o host oficial de upload, nunca para outro destino.
    parts = urlsplit(upload_url)
    if parts.scheme != "https" or parts.hostname != REELS_UPLOAD_HOST:
        raise Exception("Facebook Reels: endereço de upload inesperado na resposta da Meta.")
    return str(video_id), upload_url


def _upload_reel(page_access_token, upload_url, video_url):
    res = retry_with_backoff(
        requests.post, upload_url,
        headers={"Authorization": f"OAuth {page_access_token}", "file_url": video_url},
        exceptions=(requests.exceptions.RequestException,), timeout=60,
    )
    if res.status_code not in (200, 201) or _json(res).get("success") is not True:
        raise Exception(
            f"Facebook Reels: falha ao enviar o vídeo (status {res.status_code}, código {_graph_code(res)})"
        )


def _finish_reel(page_access_token, page_id, video_id, caption):
    """Último passo: publica. Sem retry automático (poderia duplicar)."""
    for phase in ("finish", "complete"):
        try:
            res = requests.post(
                f"{API_BASE}/{page_id}/video_reels",
                params={"upload_phase": phase, "video_id": video_id, "video_state": "PUBLISHED",
                        "description": caption or "", "access_token": page_access_token},
                timeout=60,
            )
        except requests.exceptions.RequestException:
            # Sem str(err): a mensagem do requests traz a URL com o token.
            raise Exception(
                "Facebook Reels: a resposta da publicação se perdeu; confira a Página antes de reenviar."
            ) from None
        if res.status_code in (200, 201):
            if _json(res).get("success") is True:
                return
            raise Exception("Facebook Reels: resposta inesperada da publicação; confira a Página antes de reenviar.")
        if phase == "finish" and _graph_code(res) == 100:
            continue  # valor da fase recusado: a doc também cita `complete`
        raise mark_not_published(Exception(
            f"Facebook Reels: a Meta recusou a publicação (status {res.status_code}, código {_graph_code(res)})"
        ))


def _reel_status(page_access_token, video_id):
    try:
        res = requests.get(f"{API_BASE}/{video_id}",
                           params={"fields": "status", "access_token": page_access_token}, timeout=15)
    except requests.exceptions.RequestException:
        return None
    status = _json(res).get("status") if res.status_code == 200 else None
    return status if isinstance(status, dict) else None


def _reel_failed(status):
    if status.get("video_status") in _REELS_FAILED_VIDEO_STATES:
        return True
    phases = [status.get(name) for name in ("uploading_phase", "processing_phase", "publishing_phase")]
    phases = [phase if isinstance(phase, dict) else {} for phase in phases]
    return any(phase.get("status") == "error" for phase in phases) or phases[2].get("publish_status") == "error"


def _wait_reel_published(page_access_token, video_id):
    deadline = time.monotonic() + REELS_POLL_SECONDS
    while True:
        status = _reel_status(page_access_token, video_id)
        if status:
            if _reel_failed(status):
                # A Meta declarou erro: o Reel não foi ao ar.
                raise mark_not_published(Exception(
                    f"Facebook Reels: a Meta recusou o vídeo no processamento (estado {status.get('video_status')})."
                ))
            publishing = status.get("publishing_phase")
            if isinstance(publishing, dict) and publishing.get("publish_status") == "published":
                return
        if time.monotonic() >= deadline:
            raise Exception(
                "Facebook Reels: a Meta não confirmou a publicação em 5 min; confira a Página antes de reenviar."
            )
        time.sleep(REELS_POLL_INTERVAL)


def post_reel_as_page(page_access_token, page_id, video_url, caption):
    """Publica um Reel na Página com o vídeo por URL pública (assinada, 3600 s).

    Falha até o upload (inclusive) = nada publicado (`mark_not_published` -> failed).
    Depois do `finish`, resposta perdida ou confirmação que não chega = sem marca
    (o publicador grava `unknown`); erro declarado pela Meta = failed."""
    try:
        video_id, upload_url = _start_reel_upload(page_access_token, page_id)
        _upload_reel(page_access_token, upload_url, video_url)
    except Exception as err:
        raise mark_not_published(err)
    _finish_reel(page_access_token, page_id, video_id, caption)
    _wait_reel_published(page_access_token, video_id)
    return {"id": video_id}

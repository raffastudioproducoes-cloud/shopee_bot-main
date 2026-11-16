import os
import requests
import time
import logging
from enum import StrEnum
from urllib.parse import quote
from api.utils.log_sanitizer import sanitize_log_data

for _logger_name in ("httpx", "httpcore", "urllib3"):
    logging.getLogger(_logger_name).setLevel(logging.WARNING)

from shopee_bot.utils import retry_with_backoff, mark_not_published


API_URL = "https://graph.threads.net"
API_VERSION = "v1.0"
APP_ID = os.environ.get("THREADS_APP_ID")
SECRET = os.environ.get("THREADS_SECRET")
PERMISSIONS = os.environ.get("THREADS_PERMISSIONS")
CALLBACK_URL = os.environ.get("THREADS_CALLBACK_URL")


class MediaType(StrEnum):
    TEXT = 'TEXT'
    IMAGE = 'IMAGE'
    VIDEO = 'VIDEO'
    CAROUSEL = 'CAROUSEL'


def _remove_non_utf8(text):
    return bytes(text, "utf-8").decode("utf-8", "ignore")


class ThreadsApiError(Exception):
    """Erro HTTP confirmado da Meta, sem URL (que contém token e texto do post)."""

    def __init__(self, stage: str, status_code: int, meta_code=None, meta_subcode=None, detail=""):
        self.stage = stage
        self.status_code = status_code
        self.meta_code = meta_code
        self.meta_subcode = meta_subcode
        parts = [f"{stage}: HTTP {status_code}"]
        if meta_code is not None:
            parts.append(f"Meta code={meta_code}")
        if meta_subcode is not None:
            parts.append(f"subcode={meta_subcode}")
        if detail:
            parts.append(detail[:240])
        super().__init__(" | ".join(parts))


def _raise_exception(err_text, res, url):
    # Nunca persistir/mostrar a URL: contém access_token, mídia assinada e
    # o texto integral do post. Os códigos da Meta são a trilha diagnóstica.
    try:
        payload = res.json()
        meta = payload.get("error", {}) if isinstance(payload, dict) else {}
        if not isinstance(meta, dict):
            meta = {}
    except (ValueError, TypeError):
        meta = {}
    description = sanitize_log_data(str(meta.get("message") or ""))
    # Mensagens arbitrárias podem conter links externos; evita expor querystring.
    description = description.split("http://")[0].split("https://")[0].strip()
    raise ThreadsApiError(
        err_text, res.status_code, meta.get("code"), meta.get("error_subcode"),
        description,
    )


def _create_carousel_item(
    user_id,
    user_access_token,
    media_type,
    image_url=None,
    video_url=None
):
    url = f"""
        {API_URL}
        /{API_VERSION}
        /{user_id}
        /threads?media_type=
        {media_type}
        &is_carousel_item=true
    """.replace('\n', '').replace(' ', '')

    if media_type == MediaType.IMAGE and image_url is not None:
        url += f"&image_url={quote(image_url, safe='')}"
    elif media_type == MediaType.VIDEO and video_url is not None:
        url += f"&video_url={quote(video_url, safe='')}"

    url += f"&access_token={quote(user_access_token, safe='')}"
    res = retry_with_backoff(requests.post, url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Create Carousel Item", res, url)

    return res.json()["id"]


def _create_carousel_container(
    user_id,
    user_access_token,
    children,
    text,
    reply_to_id=None
):
    url = f"""
        {API_URL}
        /{API_VERSION}
        /{user_id}
        /threads?media_type=
        {MediaType.CAROUSEL}
        &children=
        {",".join([str(item) for item in children])}
    """.replace('\n', '').replace(' ', '')
    url += f"&text={quote(_remove_non_utf8(text), safe='')}"

    if reply_to_id is not None:
        url += f"&reply_to_id={quote(str(reply_to_id), safe='')}"

    url += f"&access_token={quote(user_access_token, safe='')}"
    res = retry_with_backoff(requests.post, url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Create Carousel Container", res, url)

    return res.json()["id"]


def _create_media_container(
    user_id,
    user_access_token,
    text,
    media_type=MediaType.TEXT,
    image_url=None,
    video_url=None,
    reply_to_id=None
):
    url = f"""
        {API_URL}
        /{API_VERSION}
        /{user_id}
        /threads?media_type=
        {media_type}
    """.replace('\n', '').replace(' ', '')
    url += f"&text={quote(_remove_non_utf8(text), safe='')}"

    if media_type == MediaType.IMAGE and image_url is not None:
        url += f"&image_url={quote(image_url, safe='')}"
    elif media_type == MediaType.VIDEO and video_url is not None:
        url += f"&video_url={quote(video_url, safe='')}"

    if reply_to_id is not None:
        url += f"&reply_to_id={quote(str(reply_to_id), safe='')}"

    url += f"&access_token={quote(user_access_token, safe='')}"
    res = retry_with_backoff(requests.post, url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Create Media Container", res, url)

    return res.json()["id"]


def _publish_media_container(user_id, user_access_token, media_container_id):
    url = f"""
        {API_URL}
        /{API_VERSION}
        /{user_id}
        /threads_publish
        ?creation_id=
        {media_container_id}

    """.replace('\n', '').replace(' ', '')

    # nota: retry aqui só cobre falha de rede/timeout (exceção antes de
    # obter resposta) — status HTTP não-2xx NÃO é retentado, para não
    # arriscar publicação duplicada em caso de sucesso silencioso.
    url += f"&access_token={quote(user_access_token, safe='')}"
    res = retry_with_backoff(requests.post, url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Publish Media Container", res, url)

    return res.json()["id"]


def _get_media_container_status(
    user_access_token,
    media_container_id,
    fields="status,error_message"
):
    url = f"""
        {API_URL}
        /{API_VERSION}
        /{media_container_id}
        ?fields=
        {fields}
    """.replace('\n', '').replace(' ', '')

    url += f"&access_token={quote(user_access_token, safe='')}"
    res = retry_with_backoff(requests.get, url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Get Media Container Status", res, url)

    return res.json()


# Doc oficial (conferida em 14/11/2026):
# - developers.facebook.com/docs/threads/posts: "Wait about 30 seconds before
#   publishing a Threads media container."
# - developers.facebook.com/docs/threads/troubleshooting: consultar o status
#   do contêiner 1x/min por no máximo 5 min; status IN_PROGRESS, FINISHED,
#   ERROR, EXPIRED, PUBLISHED.
# Publicar logo após criar gerou "code=24 subcode=4279009 The requested
# resource does not exist" (job 72c45ba8). Intervalo de 15 s (mais curto que
# o 1x/min sugerido) para não atrasar posts de texto, que ficam prontos rápido;
# no pior caso são ~20 consultas por contêiner, longe do limite de chamadas.
MIN_WAIT_BEFORE_PUBLISH_S = 30
POLL_INTERVAL_S = 15
MAX_WAIT_S = 300

# Injetáveis em teste (monkeypatch) para não dormir de verdade.
_sleep = time.sleep
_monotonic = time.monotonic


class ThreadsContainerError(Exception):
    """Contêiner não ficou pronto (ERROR/EXPIRED/timeout). Nada foi publicado."""


def _wait_container_ok(user_access_token, container_id, created_at):
    """Espera o contêiner ficar FINISHED e ao menos 30 s após a criação.

    `created_at` é o _monotonic() logo após criar o contêiner.
    """
    deadline = created_at + MAX_WAIT_S
    ready_at = created_at + MIN_WAIT_BEFORE_PUBLISH_S
    while True:
        remaining = ready_at - _monotonic()
        if remaining > 0:
            _sleep(remaining)
        res = _get_media_container_status(user_access_token, container_id)
        status = res.get("status")
        if status == "FINISHED":
            return True
        if status in ("ERROR", "EXPIRED"):
            detail = sanitize_log_data(str(res.get("error_message") or ""))[:240]
            raise ThreadsContainerError(
                f"Threads: contêiner {container_id} terminou como {status}"
                + (f" ({detail})" if detail else "")
            )
        if _monotonic() + POLL_INTERVAL_S > deadline:
            raise ThreadsContainerError(
                f"Threads: contêiner {container_id} não ficou pronto em "
                f"{MAX_WAIT_S // 60} min (último status: {status}); nada foi publicado"
            )
        ready_at = _monotonic() + POLL_INTERVAL_S


# https://developers.facebook.com/docs/threads/posts#carousel-posts
def make_carousel_post(
    user_id,
    user_access_token,
    text,
    medias,
    reply_to_id=None
):
    try:
        # Cria todos os itens antes de esperar: os 30 s de cada um correm em
        # paralelo em vez de somar 30 s por item.
        items = list()
        for media in medias:
            media_type = media["type"]
            media_url = media["url"]

            if media_type == MediaType.IMAGE:
                item_id = _create_carousel_item(
                    user_id,
                    user_access_token,
                    MediaType.IMAGE,
                    image_url=media_url,
                )
            else:
                item_id = _create_carousel_item(
                    user_id,
                    user_access_token,
                    MediaType.VIDEO,
                    video_url=media_url,
                )
            items.append((item_id, _monotonic()))

        for item_id, created_at in items:
            _wait_container_ok(user_access_token, item_id, created_at)
        children = [item_id for item_id, _ in items]

        carousel_container_id = _create_carousel_container(
            user_id,
            user_access_token,
            children,
            text,
            reply_to_id
        )
        created_at = _monotonic()

        _wait_container_ok(user_access_token, carousel_container_id, created_at)
    except Exception as err:
        # Nada chegou ao threads_publish: nenhum post ficou público.
        mark_not_published(err)
        raise

    threads_id = _publish_media_container(
        user_id,
        user_access_token,
        carousel_container_id
    )
    return threads_id


def make_post(
    user_id,
    user_access_token,
    text,
    media_type=MediaType.TEXT,
    image_url=None,
    video_url=None,
    reply_to_id=None
):
    try:
        media_container_id = _create_media_container(
            user_id,
            user_access_token,
            text,
            media_type,
            image_url,
            video_url,
            reply_to_id
        )
        created_at = _monotonic()

        _wait_container_ok(user_access_token, media_container_id, created_at)
    except Exception as err:
        # Nada chegou ao threads_publish: nenhum post ficou público.
        mark_not_published(err)
        raise

    threads_id = _publish_media_container(
        user_id,
        user_access_token,
        media_container_id
    )

    return threads_id


def get_app_access_token():
    url = f"""
        {API_URL}
        /oauth/access_token
        ?client_id=
        {APP_ID}
        &client_secret=
        {SECRET}
        &grant_type=client_credentials
    """.replace('\n', '').replace(' ', '')

    res = requests.get(url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Get APP Access Token", res, url)

    return res.json()


###
# User AUTH
###
def get_user_auth_url():
    # for some reason, the first step do not uses the subdomain "graph"
    # https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions#etapa-1--receber-autoriza--o
    api_url = "https://threads.net"
    return f"""
        {api_url}
        /oauth/authorize
        ?client_id=
        {APP_ID}
        &redirect_uri=
        {CALLBACK_URL}
        &scope=
        {PERMISSIONS}
        &response_type=code
    """.replace('\n', '').replace(' ', '')


def _get_user_short_lived_token(code):
    # https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions#etapa-2--trocar-o-c-digo-por-um-token
    url = f"""
        {API_URL}
        /oauth/access_token
        ?client_id=
        {APP_ID}
        &client_secret=
        {SECRET}
        &grant_type=authorization_code
        &redirect_uri=
        {CALLBACK_URL}
        &code={quote(code, safe='')}
    """.replace('\n', '').replace(' ', '')

    res = requests.get(url)
    if res.status_code not in [200, 201]:
        _raise_exception(
            "Failed to Get User Short-Lived Access Token",
            res,
            url
        )
    return res.json()


def _get_user_long_lived_token(short_lived_access_token):
    # https://developers.facebook.com/docs/threads/get-started/long-lived-tokens?locale=en_US#get-a-long-lived-token
    url = f"""
        {API_URL}
        /access_token
        ?client_secret=
        {SECRET}
        &grant_type=th_exchange_token
        &access_token=
        {short_lived_access_token}
    """.replace('\n', '').replace(' ', '')

    res = requests.get(url)
    if res.status_code not in [200, 201]:
        _raise_exception(
            "Failed to Get User Long-Lived Access Token",
            res,
            url
        )

    return res.json()


def get_user_auth_id_token(code):
    user_data = _get_user_short_lived_token(code)
    user_id = user_data["user_id"]
    short_lived_token = user_data["access_token"]

    token_data = _get_user_long_lived_token(short_lived_token)
    access_token = token_data["access_token"]

    return user_id, access_token


def refresh_user_token(user_access_token):
    url = f"""
        {API_URL}
        /refresh_access_token
        ?grant_type=th_refresh_token
        &access_token=
        {user_access_token}
    """.replace('\n', '').replace(' ', '')

    res = requests.get(url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Refresh User ID", res, url)

    return res.json()


def get_user_id(user_access_token):
    url = f"""
        {API_URL}
        /{API_VERSION}
        /me
        ?access_token=
        {user_access_token}
    """.replace('\n', '').replace(' ', '')

    res = requests.get(url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Get User ID", res, url)

    return res.json()["id"]

import os
import requests
import time
from enum import StrEnum
from urllib.parse import quote

from shopee_bot.utils import retry_with_backoff


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


def _raise_exception(err_text, res, url):
    raise Exception(
        "{0}:\nStatus: {1}\nURL: {2}\nText: {3}".format(
            err_text,
            res.status_code,
            url,
            res.text
        )
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
        &access_token=
        {user_access_token}
        &is_carousel_item=true
    """.replace('\n', '').replace(' ', '')

    if media_type == MediaType.IMAGE and image_url is not None:
        url += f"&image_url={quote(image_url, safe='')}"
    elif media_type == MediaType.VIDEO and video_url is not None:
        url += f"&video_url={quote(video_url, safe='')}"

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
        &access_token=
        {user_access_token}
    """.replace('\n', '').replace(' ', '')
    url += f"&text={quote(_remove_non_utf8(text), safe='')}"

    if reply_to_id is not None:
        url += f"&reply_to_id={quote(str(reply_to_id), safe='')}"

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
        &access_token=
        {user_access_token}
    """.replace('\n', '').replace(' ', '')
    url += f"&text={quote(_remove_non_utf8(text), safe='')}"

    if media_type == MediaType.IMAGE and image_url is not None:
        url += f"&image_url={quote(image_url, safe='')}"
    elif media_type == MediaType.VIDEO and video_url is not None:
        url += f"&video_url={quote(video_url, safe='')}"

    if reply_to_id is not None:
        url += f"&reply_to_id={quote(str(reply_to_id), safe='')}"

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
        &access_token=
        {user_access_token}

    """.replace('\n', '').replace(' ', '')

    # nota: retry aqui só cobre falha de rede/timeout (exceção antes de
    # obter resposta) — status HTTP não-2xx NÃO é retentado, para não
    # arriscar publicação duplicada em caso de sucesso silencioso.
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
        &access_token=
        {user_access_token}
    """.replace('\n', '').replace(' ', '')

    res = retry_with_backoff(requests.get, url)
    if res.status_code not in [200, 201]:
        _raise_exception("Failed to Get Media Container Status", res, url)

    return res.json()


# https://developers.facebook.com/docs/threads/troubleshooting#publishing-does-not-return-a-media-id
def _wait_container_ok(user_access_token, container_id):
    while True:
        res = _get_media_container_status(user_access_token, container_id)
        status = res["status"] if "status" in res else None
        error_message = res["error_message"] if "error_message" in res else None

        if status in ["EXPIRED", "ERROR"]:
            raise Exception(
                "Cannot proceed. MDI {0} is {1}, {2}".format(
                    container_id,
                    status,
                    error_message
                )
            )

        if status != "FINISHED":
            time.sleep(1)

        elif status == "FINISHED":
            return True


# https://developers.facebook.com/docs/threads/posts#carousel-posts
def make_carousel_post(
    user_id,
    user_access_token,
    text,
    medias,
    reply_to_id=None
):
    children = list()
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

        _wait_container_ok(user_access_token, item_id)
        children.append(item_id)

    carousel_container_id = _create_carousel_container(
        user_id,
        user_access_token,
        children,
        text,
        reply_to_id
    )

    _wait_container_ok(user_access_token, carousel_container_id)

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
    media_container_id = _create_media_container(
        user_id,
        user_access_token,
        text,
        media_type,
        image_url,
        video_url,
        reply_to_id
    )

    _wait_container_ok(user_access_token, media_container_id)

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

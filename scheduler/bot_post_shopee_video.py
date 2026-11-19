"""
Publicação na Shopee Vídeo via scheduler — mesma estrutura de bot_post_tiktok.py.

Só vídeo MP4 (3–60 s), legenda até 150 e até 6 produtos vinculados
(products.product_id = itemId externo da Shopee). Fluxo: token válido
(api/shopee_video_tokens.py) → upload em partes → aguarda SUCCEEDED → capa →
edit_video_info → post_video (UMA vez). Até edit_video_info nada é público:
falhas viram "failed". Erro de rede/timeout no post_video vira "unknown" depois
de consultar get_video_list; nunca repetir post_video às cegas.
"""

import os

from shopee_bot.apis.shopee_video import (
    MAX_CAPTION_LENGTH, MAX_LINKED_PRODUCTS, MAX_VIDEO_SIZE, ShopeeVideoAuthorization,
    ShopeeVideoClient, ShopeeVideoError, ShopeeVideoRejected,
)
from shopee_bot.apis.tiktok import _video_duration_seconds as video_duration_seconds
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, posts
from shopee_bot.database.activities import insert_activities, activity_metadata_wrapper
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.scheduler.media_delivery import MediaDownloadError, local_file
from shopee_bot.scheduler.profile_scope import require_profile_id
from shopee_bot.scheduler.publication_context import mark_external_delivery
from shopee_bot.scheduler.publication_result import failed, succeeded, unknown

NETWORK = "shopee_video"
UPLOAD_TIMEOUT_SECONDS = 600
NO_VIDEO_MESSAGE = "Shopee Vídeo exige um vídeo MP4 — este post não tem vídeo anexado."
CAPTION_MESSAGE = f"Shopee Vídeo exige legenda de 1 a {MAX_CAPTION_LENGTH} caracteres."
NO_PRODUCT_WARNING = "Publicado sem produto vinculado: nenhum produto com ID Shopee válido."
UNKNOWN_MESSAGE = ("A Shopee não confirmou a publicação; confira o perfil Shopee Vídeo "
                   "antes de publicar de novo.")


def _tokens():
    """Import tardio (como campaign_dispatch): api.* exige a config da API nova,
    que não deve ser carregada só por importar o scheduler."""
    from shopee_bot.api import shopee_video_tokens
    return shopee_video_tokens


def _video_media(post):
    return next((m for m in post.get("medias") or [] if m.get("type") == "VIDEO"), None)


def _linked_item_ids(user_id, post_id, profile_id):
    """IDs externos válidos e únicos, na ordem do usuário, até 6; e avisos."""
    raw = posts.get_shopee_item_ids(user_id, post_id, profile_id)
    valid = [int(i) for i in raw if isinstance(i, int) and i > 0]
    ids = list(dict.fromkeys(valid))[:MAX_LINKED_PRODUCTS]
    warnings = []
    if len(valid) < len(raw):
        logger.warning("Shopee Vídeo post %s: produto sem ID Shopee numérico ignorado", post_id)
        warnings.append("Produto sem ID Shopee válido ficou fora do vídeo.")
    if not ids:
        warnings.append(NO_PRODUCT_WARNING)
    return ids, warnings


def _activity(user_id, profile_id, kind, job_id, post_id, **extra):
    insert_activities(user_id, kind, activity_metadata_wrapper({
        "network": NETWORK, "job_id": str(job_id), "post_id": post_id, **extra,
    }), profile_id=profile_id)


def _fail(ctx, stage, err, result):
    logger.warning("Shopee Vídeo job #%s falhou em %s: %s", ctx["job_id"], stage, err)
    _activity(ctx["user_id"], ctx["profile_id"], ActivityType.BOT_POST_FAILURE,
              ctx["job_id"], ctx["post_id"], stage=stage, error=str(err))
    return result(err)


def _first_cover(client, upload_id):
    """Primeira capa HTTPS; se a Shopee falhar, segue sem capa (campo opcional)."""
    try:
        covers = client.get_covers(upload_id)
    except ShopeeVideoError as err:
        logger.warning("Shopee Vídeo: capas indisponíveis (%s); publicando sem capa", type(err).__name__)
        return None
    return covers[0] if covers else None


def _external_id(confirmation, upload_id):
    first = (confirmation or [None])[0]
    if isinstance(first, dict):
        return first.get("video_id") or first.get("post_id") or upload_id
    return str(first) if first else upload_id


def _reconcile(client, upload_id):
    """Depois de resposta incerta do post_video: só consulta, nunca republica."""
    try:
        found = client.find_posted_video(upload_id)
    except ShopeeVideoError as err:
        logger.warning("Shopee Vídeo: conciliação falhou (%s)", type(err).__name__)
        return unknown(UNKNOWN_MESSAGE)
    if not found:
        return unknown(UNKNOWN_MESSAGE)
    return succeeded(found.get("video_id") or found.get("post_id") or upload_id)


def _upload_and_describe(client, video_path, caption, item_ids):
    size = os.path.getsize(video_path)
    duration = round(video_duration_seconds(video_path))
    with open(video_path, "rb") as stream:
        upload_id = client.upload_file(stream, "video.mp4", size, duration)
    client.wait_upload_result(upload_id, timeout_s=UPLOAD_TIMEOUT_SECONDS)
    client.set_video_info(upload_id, caption=caption, cover_url=_first_cover(client, upload_id),
                          product_item_ids=item_ids, ai_assisted=False)
    return upload_id


def _publish(ctx, auth, video_path, caption, item_ids):
    client = ShopeeVideoClient(
        ShopeeVideoAuthorization(auth.partner_id, auth.partner_key, auth.shopee_user_id,
                                 auth.access_token, permission_granted=True),
        sandbox=auth.sandbox, enabled=True,
    )
    try:
        upload_id = _upload_and_describe(client, video_path, caption, item_ids)
    except Exception as err:  # rascunho/upload: nada público ainda
        return None, _fail(ctx, "upload", err, failed)
    mark_external_delivery()
    try:
        confirmation = client.post_video(upload_id)["confirmation"]
    except ShopeeVideoRejected as err:
        return None, _fail(ctx, "publish", err, failed)
    except Exception as err:
        logger.warning("Shopee Vídeo: post_video incerto (%s); conciliando", type(err).__name__)
        result = _reconcile(client, upload_id)
        if result.status != "succeeded":
            return None, _fail(ctx, "publish", result.error, unknown)
        return result.external_id, None
    return _external_id(confirmation, upload_id), None


def _authorization(ctx):
    tokens = _tokens()
    try:
        return tokens.get_valid_authorization(ctx["user_id"], ctx["profile_id"]), None
    except (tokens.ShopeeVideoReconnectRequired, tokens.ShopeeVideoNotConfigured) as err:
        return None, _fail(ctx, "preflight", err, failed)
    except Exception as err:  # renovação indisponível agora; nada enviado
        logger.warning("Shopee Vídeo: autorização indisponível (%s)", type(err).__name__)
        return None, _fail(ctx, "preflight", "Não foi possível renovar o acesso à Shopee Vídeo agora.", failed)


def bot_post_shopee_video(job_id):
    logger.info(f"Running Shopee Vídeo job #{job_id}...")
    job = schedulers.get_by_id(job_id)
    ctx = {"job_id": job_id, "user_id": job["user_id"], "post_id": job["post_id"],
           "profile_id": require_profile_id(job)}
    head = posts.get(ctx["user_id"], ctx["post_id"], ctx["profile_id"])[0]
    media = _video_media(head)
    if media is None:
        return _fail(ctx, "preflight", NO_VIDEO_MESSAGE, failed)
    caption = (head.get("text") or "").strip()
    if not 0 < len(caption) <= MAX_CAPTION_LENGTH:
        return _fail(ctx, "preflight", CAPTION_MESSAGE, failed)
    item_ids, warnings = _linked_item_ids(ctx["user_id"], ctx["post_id"], ctx["profile_id"])
    auth, error = _authorization(ctx)
    if error:
        return error
    try:
        with local_file(media, MAX_VIDEO_SIZE) as video_path:
            external_id, error = _publish(ctx, auth, video_path, caption, item_ids)
    except MediaDownloadError as err:
        return _fail(ctx, "media", err, failed)
    if error:
        return error
    _activity(ctx["user_id"], ctx["profile_id"], ActivityType.BOT_POST_SUCCESS, job_id,
              ctx["post_id"], stage="publish", video_id=external_id,
              linked_products=len(item_ids), warnings=warnings)
    logger.info(f"bot_post_shopee_video job #{job_id} finished.")
    return succeeded(external_id)

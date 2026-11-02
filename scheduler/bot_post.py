from shopee_bot.apis import threads as ThreadsAPI
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, threads_credentials, posts
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.scheduler.profile_scope import require_profile_id
from shopee_bot.scheduler.publication_context import mark_external_delivery
from shopee_bot.scheduler.media_delivery import STORAGE_PREFIX, delivery_url
from shopee_bot.scheduler.publication_result import succeeded, unknown, failed


MEDIA_FILE_MISSING_MESSAGE = (
    "Mídia antiga não está no Supabase Storage. Reenvie a mídia do post."
)


def _ensure_media_ready(medias):
    """Rejeita referências legadas: novos uploads são sempre Supabase Storage."""
    if any(not m["file_path"].startswith(STORAGE_PREFIX) for m in medias):
        raise FileNotFoundError(MEDIA_FILE_MISSING_MESSAGE)


def _carousel_post(user_data, post, reply_to_id=None):
    _ensure_media_ready(post["medias"])
    medias, cleanups = [], []
    try:
        for media in post["medias"]:
            url, cleanup = delivery_url(media)
            cleanups.append(cleanup)
            medias.append({"type": media["type"], "url": url})
        mark_external_delivery()
        return ThreadsAPI.make_carousel_post(
            user_data["threads_user_id"],
            user_data["threads_access_token"],
            post["text"],
            medias,
            reply_to_id
        )
    finally:
        for cleanup in cleanups:
            cleanup()


def _media_post(user_data, post, reply_to_id=None):
    _ensure_media_ready(post["medias"])
    media = post["medias"][0]
    url, cleanup = delivery_url(media)
    kind = {"IMAGE": {"media_type": "IMAGE", "image_url": url}}.get(
        media["type"], {"media_type": "VIDEO", "video_url": url}
    )
    try:
        mark_external_delivery()
        return ThreadsAPI.make_post(
            user_data["threads_user_id"],
            user_data["threads_access_token"],
            post["text"],
            reply_to_id=reply_to_id,
            **kind
        )
    finally:
        cleanup()


def _text_post(user_data, post, reply_to_id=None):
    threads_user_id = user_data["threads_user_id"]
    threads_access_token = user_data["threads_access_token"]

    mark_external_delivery()
    return ThreadsAPI.make_post(
        threads_user_id,
        threads_access_token,
        post["text"],
        reply_to_id=reply_to_id
    )


def bot_post(job_id):
    logger.info(f"Running job #{job_id}...")

    job_data = schedulers.get_by_id(job_id)
    user_id = job_data["user_id"]
    post_id = job_data["post_id"]
    profile_id = require_profile_id(job_data)

    user_data = threads_credentials.get_by_user_id(user_id, profile_id)
    if not user_data:
        # registrado como falha do post pelo listener do scheduler
        raise RuntimeError("Credencial do Threads não conectada. Conecte em Credenciais.")
    username = user_data["username"]
    logger.info(f"job #{job_id} is {username}'s.")

    last_post_id = None
    post_data = posts.get(user_id, post_id, profile_id)
    published_parts = 0

    for part_index, post in enumerate(post_data):
        try:
            if len(post["medias"]) > 1:
                last_post_id = _carousel_post(user_data, post, last_post_id)
            elif len(post["medias"]) > 0:
                last_post_id = _media_post(user_data, post, last_post_id)
            else:
                last_post_id = _text_post(user_data, post, last_post_id)
            published_parts += 1
        except Exception as err:
            logger.exception(
                f"job #{job_id} for {username} falhou na parte "
                f"{part_index + 1}/{len(post_data)}: {err}"
            )
            insert_activities(
                user_id,
                ActivityType.BOT_POST_FAILURE,
                activity_metadata_wrapper({
                    "network": "threads",
                    "job_id": str(job_id),
                    "post_id": post_id,
                    "stage": "publish",
                    "part_index": part_index,
                    "total_parts": len(post_data),
                    "published_parts": published_parts,
                    "error": str(err),
                }),
                profile_id=profile_id
            )
            # não continua a thread: partes seguintes seriam replies de
            # um post que nunca saiu (reply_to_id inválido).
            # Uma rejeição 4xx na CRIAÇÃO do contêiner é definitiva:
            # nenhuma publicação foi solicitada. Erros no publish (ou após
            # partes anteriores) continuam incertos para evitar duplicação.
            if (published_parts == 0 and
                    isinstance(err, ThreadsAPI.ThreadsApiError) and
                    err.stage.startswith("Failed to Create") and
                    400 <= err.status_code < 500):
                return failed(err)
            return unknown(err)

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "network": "threads",
            "job_id": str(job_id),
            "post_id": post_id,
            "stage": "publish",
            "published_parts": published_parts,
        }),
        profile_id=profile_id
    )
    logger.info(f"bot_post job #{job_id} for {username} finished.")
    return succeeded(last_post_id)

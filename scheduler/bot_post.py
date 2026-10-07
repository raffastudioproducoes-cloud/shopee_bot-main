import os

from shopee_bot.apis import threads as ThreadsAPI
from shopee_bot.apis.cloudinary import cloudinary as CloudinaryAPI
from shopee_bot.apis.cloudinary import ensure_configured as ensure_media_storage
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, threads_credentials, posts
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.utils import retry_with_backoff


MEDIA_FILE_MISSING_MESSAGE = (
    "Arquivo de mídia não encontrado no servidor (o disco do servidor é "
    "apagado a cada deploy/reinício). Reenvie a mídia do post."
)


def _ensure_media_ready(medias):
    """Pré-condições do upload, com mensagem clara em vez de stack trace."""
    ensure_media_storage()
    if any(not os.path.isfile(m["file_path"]) for m in medias):
        raise FileNotFoundError(MEDIA_FILE_MISSING_MESSAGE)


def _carousel_post(user_data, post, reply_to_id=None):
    threads_user_id = user_data["threads_user_id"]
    threads_access_token = user_data["threads_access_token"]
    _ensure_media_ready(post["medias"])

    medias = list()
    media_ids = list()
    for media in post["medias"]:
        res = None
        if media["type"] == "IMAGE":
            res = retry_with_backoff(
                CloudinaryAPI.uploader.upload,
                media["file_path"],
                format="jpg"
            )
        else:
            res = retry_with_backoff(
                CloudinaryAPI.uploader.upload,
                media["file_path"],
                resource_type="video"
            )

        medias.append({
            "type": media["type"],
            "url": res["url"]
        })
        media_ids.append(res["public_id"])

    item_id = ThreadsAPI.make_carousel_post(
        threads_user_id,
        threads_access_token,
        post["text"],
        medias,
        reply_to_id
    )

    for media_id in media_ids:
        CloudinaryAPI.uploader.destroy(media_id)

    return item_id


def _media_post(user_data, post, reply_to_id=None):
    threads_user_id = user_data["threads_user_id"]
    threads_access_token = user_data["threads_access_token"]

    _ensure_media_ready(post["medias"])
    res = None
    item_id = None
    media = post["medias"][0]
    if media["type"] == "IMAGE":
        res = retry_with_backoff(
            CloudinaryAPI.uploader.upload,
            media["file_path"],
            format="jpg"
        )

        item_id = ThreadsAPI.make_post(
            threads_user_id,
            threads_access_token,
            post["text"],
            media_type="IMAGE",
            image_url=res["url"],
            reply_to_id=reply_to_id
        )
    else:
        res = retry_with_backoff(
            CloudinaryAPI.uploader.upload,
            media["file_path"],
            resource_type="video"
        )

        item_id = ThreadsAPI.make_post(
            threads_user_id,
            threads_access_token,
            post["text"],
            media_type="VIDEO",
            video_url=res["url"],
            reply_to_id=reply_to_id
        )

    CloudinaryAPI.uploader.destroy(res["public_id"])
    return item_id


def _text_post(user_data, post, reply_to_id=None):
    threads_user_id = user_data["threads_user_id"]
    threads_access_token = user_data["threads_access_token"]

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
    # perfil dono do post: credencial e atividades ficam nele (None = job antigo)
    profile_id = job_data.get("profile_id")

    user_data = threads_credentials.get_by_user_id(user_id, profile_id)
    if not user_data:
        # registrado como falha do post pelo listener do scheduler
        raise RuntimeError("Credencial do Threads não conectada. Conecte em Credenciais.")
    username = user_data["username"]
    logger.info(f"job #{job_id} is {username}'s.")

    last_post_id = None
    post_data = posts.get(user_id, post_id)
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
                    "job_id": str(job_id),
                    "post_id": post_id,
                    "part_index": part_index,
                    "total_parts": len(post_data),
                    "published_parts": published_parts,
                    "error": str(err),
                }),
                profile_id=profile_id
            )
            # não continua a thread: partes seguintes seriam replies de
            # um post que nunca saiu (reply_to_id inválido).
            return

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "job_id": str(job_id),
            "post_id": post_id,
            "published_parts": published_parts,
        }),
        profile_id=profile_id
    )
    logger.info(f"bot_post job #{job_id} for {username} finished.")

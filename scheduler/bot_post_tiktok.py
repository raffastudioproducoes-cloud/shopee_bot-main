"""
Publicação no TikTok via scheduler — mesma estrutura de bot_post.py
(Threads), adaptada pra uma limitação própria da TikTok: só publica
vídeo (ver apis/tiktok.py). TikTok também não suporta thread
multi-parte como o Threads (reply chain) — só a head do post (parte 0)
é publicada; partes seguintes, se existirem, são ignoradas.
"""

from shopee_bot.apis import tiktok as TikTokAPI
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, tiktok_credentials, posts
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType


def _video_media(post):
    for media in post.get("medias") or []:
        if media.get("type") == "VIDEO":
            return media
    return None


def bot_post_tiktok(job_id):
    logger.info(f"Running TikTok job #{job_id}...")

    job_data = schedulers.get_by_id(job_id)
    user_id = job_data["user_id"]
    post_id = job_data["post_id"]
    # perfil dono do post: credencial e atividades ficam nele (None = job antigo)
    profile_id = job_data.get("profile_id")

    user_data = tiktok_credentials.get_by_user_id(user_id, profile_id)
    username = user_data["username"]
    logger.info(f"TikTok job #{job_id} is {username}'s.")

    post_data = posts.get(user_id, post_id)
    head_post = post_data[0]
    media = _video_media(head_post)

    # TikTok não aceita post de texto puro — exige vídeo. Se a head da
    # thread não tem vídeo anexado, falha com atividade clara em vez de
    # tentar publicar (não deixa a exceção da API estourar/confundir
    # com falha de rede).
    if media is None:
        message = (
            "TikTok exige um vídeo para publicar — este post não tem "
            "mídia de vídeo anexada."
        )
        logger.warning(f"TikTok job #{job_id} para {username}: {message}")
        insert_activities(
            user_id,
            ActivityType.BOT_POST_FAILURE,
            activity_metadata_wrapper({
                "job_id": str(job_id),
                "post_id": post_id,
                "error": message,
            }),
            profile_id=profile_id
        )
        return

    try:
        publish_id = TikTokAPI.post_video(
            user_data["tiktok_user_access_token"],
            media["file_path"],
            head_post["text"],
        )
    except Exception as err:
        logger.exception(
            f"TikTok job #{job_id} para {username} falhou: {err}"
        )
        insert_activities(
            user_id,
            ActivityType.BOT_POST_FAILURE,
            activity_metadata_wrapper({
                "job_id": str(job_id),
                "post_id": post_id,
                "error": str(err),
            }),
            profile_id=profile_id
        )
        return

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "job_id": str(job_id),
            "post_id": post_id,
            "publish_id": publish_id,
        }),
        profile_id=profile_id
    )
    logger.info(f"bot_post_tiktok job #{job_id} for {username} finished.")

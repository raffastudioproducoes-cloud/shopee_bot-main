"""
Publicação no TikTok via scheduler — mesma estrutura de bot_post.py
(Threads), adaptada pra uma limitação própria da TikTok: só publica
vídeo (ver apis/tiktok.py). TikTok também não suporta thread
multi-parte como o Threads (reply chain) — só a head do post (parte 0)
é publicada; partes seguintes, se existirem, são ignoradas.
"""

import os

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


RECONNECT_MESSAGE = "Autorização do TikTok expirada — reconecte em Credenciais"


def _is_token_expired(err):
    text = str(err)
    return "access_token_invalid" in text or "Status: 401" in text


def _refresh_tokens(user_id, profile_id, user_data):
    """Renova o access_token e grava os novos tokens ANTES de qualquer
    nova tentativa (o refresh_token pode rotacionar). Devolve o novo
    access_token ou None se a renovação falhou."""
    refresh_token = user_data.get("tiktok_refresh_token")
    if not refresh_token:
        return None
    # App único da plataforma (env); cai pro app da credencial se faltar
    client_key = os.environ.get("TIKTOK_CLIENT_KEY") or user_data["tiktok_app_id"]
    client_secret = (
        os.environ.get("TIKTOK_CLIENT_SECRET") or user_data["tiktok_secret"]
    )
    try:
        tokens = TikTokAPI.refresh_user_token(
            client_key, client_secret, refresh_token
        )
        if not tokens.get("access_token"):
            return None
        tiktok_credentials.update_tokens(user_id, profile_id, tokens)
    except Exception as err:
        # sem str(err): o corpo da resposta pode citar tokens
        logger.warning(f"TikTok refresh falhou: {type(err).__name__}")
        return None
    return tokens["access_token"]


def _post_with_refresh(user_id, profile_id, user_data, media, text):
    try:
        return TikTokAPI.post_video(
            user_data["tiktok_user_access_token"], media["file_path"], text
        )
    except Exception as err:
        if not _is_token_expired(err):
            raise
    logger.info("TikTok access token expirado — renovando com refresh token.")
    new_token = _refresh_tokens(user_id, profile_id, user_data)
    if not new_token:
        try:
            tiktok_credentials.mark_needs_reconnect(
                user_id, profile_id, RECONNECT_MESSAGE
            )
        except Exception as err:
            logger.warning(f"TikTok: não marcou reconexão: {type(err).__name__}")
        raise TikTokAPI.TikTokAPIError(RECONNECT_MESSAGE)
    return TikTokAPI.post_video(new_token, media["file_path"], text)


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
        publish_id = _post_with_refresh(
            user_id, profile_id, user_data, media, head_post["text"]
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

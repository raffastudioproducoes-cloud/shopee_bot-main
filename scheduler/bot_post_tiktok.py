"""
Publicação no TikTok via scheduler — mesma estrutura de bot_post.py
(Threads), adaptada pra uma limitação própria da TikTok: só publica
vídeo (ver apis/tiktok.py). TikTok também não suporta thread
multi-parte como o Threads (reply chain) — só a head do post (parte 0)
é publicada; partes seguintes, se existirem, são ignoradas.

Consentimento (Content Sharing Guidelines): envia somente as escolhas que o
usuário gravou ao criar/agendar (posts.tiktok_options, ou o item do snapshot
da campanha). Sem elas, falha com "Reconfirme as opções do TikTok" antes de
qualquer chamada ao TikTok. Modo "draft" manda o vídeo para os rascunhos do
app TikTok (escopo video.upload); "direct" publica (video.publish).
"""

import os

from shopee_bot.apis import tiktok as TikTokAPI
from shopee_bot.api.tiktok_options import parse_stored
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, tiktok_credentials, posts
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.scheduler.media_delivery import MediaDownloadError, local_file
from shopee_bot.scheduler.profile_scope import require_profile_id
from shopee_bot.utils import mark_not_published, was_not_published
from shopee_bot.scheduler.publication_context import mark_external_delivery
from shopee_bot.scheduler.publication_result import failed, succeeded, unknown


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


def _send(token, video_path, text, options):
    if options.mode == "draft":
        return TikTokAPI.upload_video_draft(
            token, video_path, before_publish=mark_external_delivery,
        )
    return TikTokAPI.post_video(
        token, video_path, text, options, before_publish=mark_external_delivery,
    )


def _post_with_refresh(user_id, profile_id, user_data, video_path, text, options):
    try:
        return _send(user_data["tiktok_user_access_token"], video_path, text, options)
    except Exception as err:
        if not _is_token_expired(err):
            raise
        expired_before_publish = was_not_published(err)
    logger.info("TikTok access token expirado — renovando com refresh token.")
    new_token = _refresh_tokens(user_id, profile_id, user_data)
    if not new_token:
        try:
            tiktok_credentials.mark_needs_reconnect(
                user_id, profile_id, RECONNECT_MESSAGE
            )
        except Exception as err:
            logger.warning(f"TikTok: não marcou reconexão: {type(err).__name__}")
        reconnect = TikTokAPI.TikTokAPIError(RECONNECT_MESSAGE)
        raise mark_not_published(reconnect) if expired_before_publish else reconnect
    return _send(new_token, video_path, text, options)


def _fail(job_id, username, user_id, post_id, profile_id, stage, err, result):
    logger.exception(f"TikTok job #{job_id} para {username} falhou: {err}")
    insert_activities(
        user_id,
        ActivityType.BOT_POST_FAILURE,
        activity_metadata_wrapper({
            "network": "tiktok",
            "job_id": str(job_id),
            "post_id": post_id,
            "stage": stage,
            "error": str(err),
        }),
        profile_id=profile_id
    )
    return result(err)


def bot_post_tiktok(job_id):
    logger.info(f"Running TikTok job #{job_id}...")

    job_data = schedulers.get_by_id(job_id)
    user_id = job_data["user_id"]
    post_id = job_data["post_id"]
    # perfil dono do post: credencial e atividades ficam nele (None = job antigo)
    profile_id = require_profile_id(job_data)

    user_data = tiktok_credentials.get_by_user_id(user_id, profile_id)
    username = user_data["username"]
    logger.info(f"TikTok job #{job_id} is {username}'s.")

    post_data = posts.get(user_id, post_id, profile_id)
    head_post = post_data[0]
    media = _video_media(head_post)

    try:
        options = parse_stored(posts.get_tiktok_options(user_id, post_id, profile_id))
    except ValueError as err:
        # Post/campanha antigo sem consentimento registrado: nunca inventa valores.
        logger.warning(f"TikTok job #{job_id} para {username}: sem escolhas do TikTok")
        return _fail(job_id, username, user_id, post_id, profile_id, "preflight", err, failed)

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
                "network": "tiktok",
                "job_id": str(job_id),
                "post_id": post_id,
                "stage": "preflight",
                "error": message,
            }),
            profile_id=profile_id
        )
        return failed(message)

    try:
        # file_path é storage://...: baixa para um temporário (apagado ao sair).
        # Falha aqui acontece antes de qualquer chamada ao TikTok -> failed.
        with local_file(media, TikTokAPI.MAX_VIDEO_BYTES) as video_path:
            publish_id = _post_with_refresh(
                user_id, profile_id, user_data, video_path, head_post["text"], options,
            )
    except MediaDownloadError as err:
        return _fail(job_id, username, user_id, post_id, profile_id, "media", err, failed)
    except Exception as err:
        # Validação da conta/vídeo antes do init no TikTok: nada enviado.
        result = failed if was_not_published(err) else unknown
        return _fail(job_id, username, user_id, post_id, profile_id, "publish", err, result)

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "network": "tiktok",
            "job_id": str(job_id),
            "post_id": post_id,
            "stage": "draft" if options.mode == "draft" else "publish",
            "publish_id": publish_id,
        }),
        profile_id=profile_id
    )
    logger.info(f"bot_post_tiktok job #{job_id} for {username} finished.")
    return succeeded(publish_id)

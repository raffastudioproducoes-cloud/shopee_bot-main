import asyncio
from datetime import datetime, timezone

import requests

from shopee_bot.api import x_oauth
from shopee_bot.apis import x as XAPI
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, x_credentials, posts
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.scheduler.media_delivery import STORAGE_PREFIX, delivery_url
from shopee_bot.scheduler.profile_scope import require_profile_id

UNSUPPORTED_MEDIA_MESSAGE = (
    "O X só publica texto ou uma única imagem por post; este post tem "
    "outra combinação de mídia e não foi publicado."
)


def _image_bytes(media):
    path = media["file_path"]
    if not path.startswith(STORAGE_PREFIX):
        with open(path, "rb") as fh:
            return fh.read()
    url, cleanup = delivery_url(media)
    try:
        res = requests.get(url, timeout=60)
        if res.status_code != 200:
            raise Exception(f"falha ao ler a mídia salva (status {res.status_code})")
        return res.content
    finally:
        cleanup()


def _upload_media_ids(user_data, post):
    """media_ids do X para o post; [] só quando o post não tem mídia."""
    medias = post.get("medias") or []
    if not medias:
        return []
    if len(medias) != 1 or medias[0].get("type") != "IMAGE":
        raise Exception(UNSUPPORTED_MEDIA_MESSAGE)
    media = medias[0]
    return [XAPI.upload_image(
        user_data["x_access_token"], _image_bytes(media), media.get("file_name") or "image"
    )]


def _ensure_fresh_token(user_id, profile_id, user_data):
    """Renova o access_token de usuário se já expirou.

    ponytail: checagem simples de expiração, sem lock entre workers
    concorrentes — se dois jobs do mesmo usuário rodarem ao mesmo tempo
    com o token expirado, os dois tentam refresh e o X invalida o
    refresh_token anterior a cada troca, então o segundo pode falhar.
    Upgrade: lock por usuário se isso virar problema real (volume baixo
    de posts por usuário torna a corrida improvável hoje).
    """
    expires_at = user_data.get("token_expires_at")
    if not expires_at:
        return user_data

    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) < expires_at:
        return user_data

    # O token nasceu no OAuth global (X_CLIENT_ID/X_CLIENT_SECRET), que
    # tambem alimenta o teste de conexao. Nao reutilizar app_id/secret
    # legados da tabela: eles podem pertencer a outro app e o X recusaria
    # a renovacao com invalid_client.
    token_data = asyncio.run(
        x_oauth.refresh_access_token(user_data["x_refresh_token"])
    )
    x_credentials.update_tokens(user_id, profile_id, token_data)
    user_data["x_access_token"] = token_data["access_token"]
    return user_data


def bot_post_x(job_id):
    logger.info(f"Running job #{job_id}...")

    job_data = schedulers.get_by_id(job_id)
    user_id = job_data["user_id"]
    post_id = job_data["post_id"]
    profile_id = require_profile_id(job_data)

    user_data = x_credentials.get_by_user_id(user_id, profile_id)
    username = user_data["username"]
    logger.info(f"job #{job_id} is {username}'s (X).")

    try:
        user_data = _ensure_fresh_token(user_id, profile_id, user_data)
    except Exception as err:
        logger.exception(
            f"job #{job_id} for {username} falhou ao renovar token X: {err}"
        )
        insert_activities(
            user_id,
            ActivityType.BOT_POST_FAILURE,
            activity_metadata_wrapper({
                "network": "x",
                "job_id": str(job_id),
                "post_id": post_id,
                "stage": "token_refresh",
                "error": f"refresh_token: {err}",
            }),
            profile_id=profile_id
        )
        return

    last_tweet_id = None
    post_data = posts.get(user_id, post_id, profile_id)
    published_parts = 0

    for part_index, post in enumerate(post_data):
        try:
            media_ids = _upload_media_ids(user_data, post)
            tweet = XAPI.post_text(
                user_data["x_access_token"],
                post["text"],
                reply_to_id=last_tweet_id,
                **({"media_ids": media_ids} if media_ids else {}),
            )
            last_tweet_id = tweet.get("id")
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
                    "network": "x",
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
            # um tweet que nunca saiu (reply_to_id inválido).
            return

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "network": "x",
            "job_id": str(job_id),
            "post_id": post_id,
            "stage": "publish",
            "published_parts": published_parts,
        }),
        profile_id=profile_id
    )
    logger.info(f"bot_post_x job #{job_id} for {username} finished.")

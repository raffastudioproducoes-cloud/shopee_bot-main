from shopee_bot.apis import instagram as InstagramAPI
from shopee_bot.apis.cloudinary import cloudinary as CloudinaryAPI
from shopee_bot.apis.cloudinary import ensure_configured as ensure_media_storage
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, instagram_credentials, posts, products
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.scheduler.profile_scope import require_profile_id
from shopee_bot.utils import retry_with_backoff


def _first_image(post):
    return next((media for media in post.get("medias") or [] if media.get("type") == "IMAGE"), None)


def _publish_image(app_id, secret, user_access_token, ig_user_id, media, caption):
    ensure_media_storage()
    upload = retry_with_backoff(CloudinaryAPI.uploader.upload, media["file_path"], format="jpg")
    try:
        return InstagramAPI.post_image(
            app_id, secret, user_access_token, upload.get("secure_url") or upload["url"], caption, ig_user_id
        )
    finally:
        CloudinaryAPI.uploader.destroy(upload["public_id"])


def bot_post_instagram(job_id):
    """Publica um post no Instagram (conta Business/Creator do usuário).

    Igual ao Facebook: sem reply chain, só o post raiz (depth 0) via
    Graph API (media container + media_publish). Publicação real exige
    App Review aprovado pra instagram_content_publish — ver aviso no
    topo de apis/instagram.py.
    """
    logger.info(f"Running job #{job_id}...")

    job_data = schedulers.get_by_id(job_id)
    user_id = job_data["user_id"]
    post_id = job_data["post_id"]
    profile_id = require_profile_id(job_data)

    user_data = instagram_credentials.get_by_user_id(user_id, profile_id)
    username = user_data["username"]
    app_id = user_data["instagram_app_id"]
    secret = user_data["instagram_secret"]
    user_access_token = user_data["instagram_user_access_token"]
    ig_user_id = user_data["instagram_ig_user_id"]
    logger.info(f"job #{job_id} is {username}'s.")

    post_data = posts.get(user_id, post_id, profile_id)
    root_post = post_data[0]
    image = _first_image(root_post)

    try:
        if image:
            _publish_image(
                app_id, secret, user_access_token, ig_user_id, image, root_post["text"]
            )
        elif root_post["product_ids"]:
            product = products.get(user_id, root_post["product_ids"][0], profile_id)
            InstagramAPI.post_product(
                app_id, secret, user_access_token, product, ig_user_id
            )
        else:
            InstagramAPI.post_text(
                app_id, secret, user_access_token, root_post["text"], ig_user_id
            )
    except Exception as err:
        logger.exception(f"job #{job_id} for {username} falhou: {err}")
        insert_activities(
            user_id,
            ActivityType.BOT_POST_FAILURE,
            activity_metadata_wrapper({
                "network": "instagram",
                "job_id": str(job_id),
                "post_id": post_id,
                "stage": "publish",
                "error": str(err),
            }),
            profile_id=profile_id
        )
        return

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "network": "instagram",
            "job_id": str(job_id),
            "post_id": post_id,
            "stage": "publish",
        }),
        profile_id=profile_id
    )
    logger.info(f"bot_post_instagram job #{job_id} for {username} finished.")

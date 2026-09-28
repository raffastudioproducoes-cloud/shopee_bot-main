from shopee_bot.apis import facebook as FacebookAPI
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, facebook_credentials, posts, products
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType


def bot_post_facebook(job_id):
    """Publica um post na Página do Facebook do usuário.

    Diferente do Threads, o Facebook não replica a estrutura de thread
    (reply chain) — só o post raiz (depth 0) é publicado como um único
    item no feed da Página.
    """
    logger.info(f"Running job #{job_id}...")

    job_data = schedulers.get_by_id(job_id)
    user_id = job_data["user_id"]
    post_id = job_data["post_id"]

    user_data = facebook_credentials.get_by_user_id(user_id)
    username = user_data["username"]
    app_id = user_data["facebook_app_id"]
    secret = user_data["facebook_secret"]
    page_id = user_data["facebook_page_id"]
    page_access_token = user_data["facebook_page_access_token"]
    logger.info(f"job #{job_id} is {username}'s.")

    post_data = posts.get(user_id, post_id)
    root_post = post_data[0]

    try:
        if page_access_token:
            # Conectado via OAuth (Login do Facebook, api/facebook_oauth.py)
            # — token já escopado pra Página certa, funciona pra qualquer
            # usuário. Ver api/facebook_oauth.py e apis/facebook.py pro
            # histórico do problema que isso resolve (App Token só
            # enxergava Páginas do PRÓPRIO app).
            if root_post["product_ids"]:
                product = products.get(user_id, root_post["product_ids"][0])
                FacebookAPI.post_product_as_page(page_access_token, page_id, product)
            else:
                FacebookAPI.post_text_as_page(page_access_token, page_id, root_post["text"])
        else:
            # Legado: credencial per-user (app_id/secret) de antes da
            # migração pro app único — só funciona pra Páginas que o app
            # do Rafa administra.
            if root_post["product_ids"]:
                product = products.get(user_id, root_post["product_ids"][0])
                FacebookAPI.post_product(app_id, secret, page_id, product)
            else:
                FacebookAPI.post_text(app_id, secret, page_id, root_post["text"])
    except Exception as err:
        logger.exception(f"job #{job_id} for {username} falhou: {err}")
        insert_activities(
            user_id,
            ActivityType.BOT_POST_FAILURE,
            activity_metadata_wrapper({
                "job_id": str(job_id),
                "post_id": post_id,
                "error": str(err),
            })
        )
        return

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "job_id": str(job_id),
            "post_id": post_id,
        })
    )
    logger.info(f"bot_post_facebook job #{job_id} for {username} finished.")

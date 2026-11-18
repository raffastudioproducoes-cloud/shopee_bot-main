from shopee_bot.apis import facebook as FacebookAPI
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, facebook_credentials, posts, products, post_link_redirects
from shopee_bot.database.activities import (
    insert_activities, activity_metadata_wrapper
)
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.scheduler.profile_scope import require_profile_id
from shopee_bot.scheduler.publication_context import mark_external_delivery
from shopee_bot.scheduler.publication_context import active_publish_job_id
from shopee_bot.scheduler.media_delivery import delivery_url
from shopee_bot.scheduler.video_probe import probe_mp4
from shopee_bot.scheduler.publication_result import external_id, failed, succeeded, unknown
from shopee_bot.utils import mark_not_published, was_not_published


def _local_url(media):
    """URL de entrega gerada localmente; falha aqui não envia nada à rede."""
    try:
        return delivery_url(media)
    except Exception as err:
        raise mark_not_published(err)


def _not_sent(message):
    """Validação local antes de qualquer chamada ao Facebook."""
    return mark_not_published(RuntimeError(message))


def _tracked_product(product):
    """Post só de produto não passa por posts.get: o link de afiliado vai pelo
    mesmo redirecionador de cliques (/r/{token}) que o texto das outras redes."""
    link = product.get("commission_link") or product.get("original_link") or ""
    tracked = post_link_redirects.rewrite_link(link, active_publish_job_id())
    return product if tracked == link else {**product, "commission_link": tracked}


def _first_image(post):
    return next((media for media in post.get("medias") or [] if media.get("type") == "IMAGE"), None)


def _publish_image(page_access_token, page_id, media, caption):
    url, cleanup = _local_url(media)
    try:
        mark_external_delivery()
        return FacebookAPI.post_photo_as_page(page_access_token, page_id, url, caption)
    finally:
        cleanup()


ALBUM_EXTS = {"jpg", "jpeg", "png"}


def _publish_album(page_access_token, page_id, medias, caption):
    urls, cleanups = [], []
    try:
        for media in medias:
            url, cleanup = _local_url(media)
            urls.append(url)
            cleanups.append(cleanup)
        mark_external_delivery()
        return FacebookAPI.post_album_as_page(page_access_token, page_id, urls, caption)
    finally:
        for cleanup in cleanups:
            cleanup()


def _publish_video(page_access_token, page_id, media, caption):
    url, cleanup = _local_url(media)
    try:
        mark_external_delivery()
        return FacebookAPI.post_video_as_page(page_access_token, page_id, url, caption)
    finally:
        cleanup()


def _publish_reel(job_id, page_access_token, page_id, media, caption):
    """Reel com validação local antes de qualquer chamada à Meta (requisitos + 30/24 h)."""
    url, cleanup = _local_url(media)
    try:
        info = probe_mp4(url)
        problem = FacebookAPI.reel_requirements_error(media.get("file_name") or media.get("file_path"), info)
        if problem:
            raise _not_sent(problem)
        warning = FacebookAPI.reel_aspect_warning(info)
        if warning:
            logger.warning(f"job #{job_id}: {warning}")
        if info is None:
            logger.warning(f"job #{job_id}: metadados do MP4 ilegíveis; a Meta valida o Reel no processamento")
        if posts.count_facebook_reels_last_24h(page_id) >= FacebookAPI.REELS_PER_PAGE_24H:
            raise _not_sent(
                f"Facebook Reels: limite de {FacebookAPI.REELS_PER_PAGE_24H} Reels por Página em 24 h atingido. "
                "Nada foi enviado; agende para mais tarde ou publique como vídeo comum."
            )
        mark_external_delivery()
        return FacebookAPI.post_reel_as_page(page_access_token, page_id, url, caption)
    finally:
        cleanup()


def _is_album_image(media):
    name = media.get("file_name") or media.get("file_path") or ""
    return media.get("type") == "IMAGE" and name.rsplit(".", 1)[-1].lower() in ALBUM_EXTS


def _images_when_mixed(job_id, medias):
    """Facebook não mistura imagem e vídeo no mesmo post: publica o grupo de
    imagens e registra (nível warning) o que foi omitido."""
    videos = [m for m in medias if m.get("type") == "VIDEO"]
    if not videos or len(videos) == len(medias):
        return medias
    kept = [m for m in medias if m.get("type") != "VIDEO"]
    logger.warning(
        f"job #{job_id}: Facebook não mistura imagem e vídeo; "
        f"publicando {len(kept)} imagem(ns) e omitindo {len(videos)} vídeo(s): "
        f"{[m.get('file_name') for m in videos]}"
    )
    return kept


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
    profile_id = require_profile_id(job_data)

    user_data = facebook_credentials.get_by_user_id(user_id, profile_id)
    username = user_data["username"]
    app_id = user_data["facebook_app_id"]
    secret = user_data["facebook_secret"]
    page_id = user_data["facebook_page_id"]
    page_access_token = user_data["facebook_page_access_token"]
    logger.info(f"job #{job_id} is {username}'s.")

    post_data = posts.get(user_id, post_id, profile_id)
    root_post = post_data[0]
    medias = _images_when_mixed(job_id, root_post.get("medias") or [])
    image = _first_image({"medias": medias})
    external = None

    try:
        if len(medias) > 1:
            if not page_access_token:
                raise _not_sent("Facebook: álbum exige conexão OAuth com token de Página.")
            if not all(_is_album_image(media) for media in medias):
                raise _not_sent("Facebook: álbum só aceita imagens JPG/PNG; vídeo e GIF não entram no álbum.")
            external = _publish_album(page_access_token, page_id, medias, root_post["text"])
        elif medias and medias[0].get("type") == "VIDEO":
            if not page_access_token:
                raise _not_sent("Facebook: vídeo exige conexão OAuth com token de Página.")
            # Escolha gravada ao agendar; post antigo sem escolha = vídeo comum.
            if posts.get_facebook_reels(user_id, post_id, profile_id):
                external = _publish_reel(job_id, page_access_token, page_id, medias[0], root_post["text"])
            else:
                external = _publish_video(page_access_token, page_id, medias[0], root_post["text"])
        elif image:
            if not page_access_token:
                raise _not_sent("Facebook: imagem exige conexão OAuth com token de Página.")
            external = _publish_image(page_access_token, page_id, image, root_post["text"])
        elif page_access_token:
            # Conectado via OAuth (Login do Facebook, api/facebook_oauth.py)
            # — token já escopado pra Página certa, funciona pra qualquer
            # usuário. Ver api/facebook_oauth.py e apis/facebook.py pro
            # histórico do problema que isso resolve (App Token só
            # enxergava Páginas do PRÓPRIO app).
            if root_post["product_ids"]:
                product = _tracked_product(products.get(user_id, root_post["product_ids"][0], profile_id))
                mark_external_delivery()
                external = FacebookAPI.post_product_as_page(page_access_token, page_id, product)
            else:
                mark_external_delivery()
                external = FacebookAPI.post_text_as_page(page_access_token, page_id, root_post["text"])
        else:
            # Legado: credencial per-user (app_id/secret) de antes da
            # migração pro app único — só funciona pra Páginas que o app
            # do Rafa administra.
            if root_post["product_ids"]:
                product = _tracked_product(products.get(user_id, root_post["product_ids"][0], profile_id))
                mark_external_delivery()
                external = FacebookAPI.post_product(app_id, secret, page_id, product)
            else:
                mark_external_delivery()
                external = FacebookAPI.post_text(app_id, secret, page_id, root_post["text"])
    except Exception as err:
        logger.exception(f"job #{job_id} for {username} falhou: {err}")
        insert_activities(
            user_id,
            ActivityType.BOT_POST_FAILURE,
            activity_metadata_wrapper({
                "network": "facebook",
                "job_id": str(job_id),
                "post_id": post_id,
                "stage": "publish",
                "error": str(err),
            }),
            profile_id=profile_id
        )
        # Validação local ou mídia indisponível: nada foi enviado ao Facebook.
        return failed(err) if was_not_published(err) else unknown(err)

    insert_activities(
        user_id,
        ActivityType.BOT_POST_SUCCESS,
        activity_metadata_wrapper({
            "network": "facebook",
            "job_id": str(job_id),
            "post_id": post_id,
            "stage": "publish",
        }),
        profile_id=profile_id
    )
    logger.info(f"bot_post_facebook job #{job_id} for {username} finished.")
    # /photos devolve `id` da foto e `post_id` do post; métricas por post precisam do post.
    if isinstance(external, dict) and external.get("post_id"):
        external = external["post_id"]
    return succeeded(external_id(external))

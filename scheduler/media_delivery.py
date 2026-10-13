"""URL que a Meta consegue baixar para uma mídia de post.

Mídia durável (`storage://bucket/chave`, criada pelo /posts/batch) vira URL
assinada e temporária do Supabase Storage; o bucket é privado. Mídia legada
(caminho em disco) continua indo pelo Cloudinary, que o chamador limpa depois.
"""

from shopee_bot.utils import retry_with_backoff

STORAGE_PREFIX = "storage://"
SIGNED_URL_TTL = 3600  # s; cobre o polling de vídeo/Reels do Instagram


def _storage():
    from shopee_bot.api.database import get_supabase
    return get_supabase().storage


def _noop():
    return None


def _upload_legacy(media):
    from shopee_bot.apis.cloudinary import cloudinary as CloudinaryAPI
    from shopee_bot.apis.cloudinary import ensure_configured

    ensure_configured()
    if media.get("type") == "VIDEO":
        upload = retry_with_backoff(CloudinaryAPI.uploader.upload, media["file_path"], resource_type="video")
    else:
        upload = retry_with_backoff(CloudinaryAPI.uploader.upload, media["file_path"], format="jpg")
    public_id = upload["public_id"]
    return (
        upload.get("secure_url") or upload["url"],
        lambda: CloudinaryAPI.uploader.destroy(public_id),
    )


def delivery_url(media):
    """Retorna `(url, cleanup)`; chame `cleanup()` depois de publicar."""
    path = media["file_path"]
    if not path.startswith(STORAGE_PREFIX):
        return _upload_legacy(media)
    bucket, _, key = path[len(STORAGE_PREFIX):].partition("/")
    if not bucket or not key:
        raise ValueError("Referência de mídia durável inválida.")
    signed = _storage().from_(bucket).create_signed_url(key, SIGNED_URL_TTL)
    return signed["signedURL"], _noop

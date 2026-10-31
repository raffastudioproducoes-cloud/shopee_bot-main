"""Entrega de mídia exclusivamente pelo Supabase Storage privado.

Mídias novas são `storage://bucket/chave`; referências antigas em disco
não podem ser publicadas e exigem reenvio do arquivo ao Supabase Storage.
"""

STORAGE_PREFIX = "storage://"
SIGNED_URL_TTL = 3600  # s; cobre o polling de vídeo/Reels do Instagram


def _storage():
    from shopee_bot.api.database import get_supabase
    return get_supabase().storage


def _noop():
    return None


def delivery_url(media):
    """Retorna `(url, cleanup)`; chame `cleanup()` depois de publicar."""
    path = media["file_path"]
    if not path.startswith(STORAGE_PREFIX):
        raise FileNotFoundError(
            "Mídia antiga fora do Supabase Storage. Reenvie a mídia do post."
        )
    bucket, _, key = path[len(STORAGE_PREFIX):].partition("/")
    if not bucket or not key:
        raise ValueError("Referência de mídia durável inválida.")
    signed = _storage().from_(bucket).create_signed_url(key, SIGNED_URL_TTL)
    return signed["signedURL"], _noop

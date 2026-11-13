"""Entrega de mídia exclusivamente pelo Supabase Storage privado.

Mídias novas são `storage://bucket/chave`; referências antigas em disco
não podem ser publicadas e exigem reenvio do arquivo ao Supabase Storage.
"""

import os
import tempfile
from contextlib import contextmanager

import requests

STORAGE_PREFIX = "storage://"
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
DOWNLOAD_TIMEOUT = (10, 60)  # s (conexão, leitura)
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


class MediaDownloadError(Exception):
    """Falha ao baixar a mídia do Storage; a mensagem nunca traz a URL assinada."""


@contextmanager
def local_file(media, max_bytes):
    """Entrega a mídia como arquivo local (para APIs que exigem upload de arquivo).

    Baixa o objeto do Storage privado via URL assinada para um temporário,
    recusando mais de `max_bytes`, e o apaga ao sair. Nada é enviado à rede
    de destino aqui: toda falha de resolução/download sai como MediaDownloadError,
    sempre antes da publicação (erros do corpo do `with` não são alterados).
    """
    try:
        url, cleanup = delivery_url(media)
    except (FileNotFoundError, ValueError) as err:
        raise MediaDownloadError(str(err)) from None
    except Exception as err:
        raise MediaDownloadError(
            f"Não foi possível acessar a mídia no armazenamento ({type(err).__name__})."
        ) from None
    suffix = os.path.splitext(media["file_path"])[1][:10]
    fd, tmp_path = tempfile.mkstemp(prefix="media-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as out:
            _download(url, out, max_bytes)
        yield tmp_path
    finally:
        cleanup()
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _download(url, out, max_bytes):
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as res:
            if res.status_code != 200:
                raise MediaDownloadError(
                    f"Não foi possível baixar a mídia do armazenamento (HTTP {res.status_code})."
                )
            total = 0
            for chunk in res.iter_content(DOWNLOAD_CHUNK_BYTES):
                total += len(chunk)
                if total > max_bytes:
                    raise MediaDownloadError("A mídia excede o tamanho máximo permitido.")
                out.write(chunk)
    except requests.RequestException as err:
        # sem str(err): a mensagem do requests inclui a URL assinada
        raise MediaDownloadError(
            f"Falha de rede ao baixar a mídia do armazenamento ({type(err).__name__})."
        ) from None
    if total == 0:
        raise MediaDownloadError("A mídia baixada está vazia.")

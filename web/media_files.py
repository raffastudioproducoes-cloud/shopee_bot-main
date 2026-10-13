"""Remoção de arquivos de mídia local no Flask."""

import logging
import os

logger = logging.getLogger(__name__)


def remove_local_media(file_path: str) -> None:
    """Apaga mídia em disco. `storage://` (mídia durável do Supabase Storage,
    gravada pela API) não é arquivo: ignora em vez de estourar 500 — o objeto
    é removido pelo DELETE da API (`_remove_media_file`)."""
    if file_path.startswith("storage://"):
        logger.warning("Mídia durável %s não removida pelo Flask", file_path)
        return
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass

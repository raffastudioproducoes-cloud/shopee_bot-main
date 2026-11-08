"""Pipeline comum dos uploads: nunca persiste MP4 original não sanitizado."""

from __future__ import annotations

from .media_sanitizer import (
    MediaSanitizerError,
    SanitizedMedia,
    _validate_declared_type,
    detect_media_type,
    sanitize_media_upload,
    validate_video_before_reencoding,
)
from .video_processor import process_video_upload


def prepare_media_upload(
    content: bytes | bytearray,
    *,
    filename: str | None,
    content_type: str | None,
    max_bytes: int,
) -> SanitizedMedia:
    """Recebe MP4 com metadados conhecidos, decodifica e sanitiza a saída.

    O validador de Storage continua estrito. Para imagem, preserva o caminho
    existente (Pillow reencoda pixels). Para vídeo, rejeita header/tipo falsos
    ANTES de invocar ffmpeg e valida novamente os bytes já reconstruídos.
    """
    if len(content) > max_bytes:
        raise MediaSanitizerError("arquivo excede o tamanho máximo")
    detected = detect_media_type(content)
    if detected.media_type == "VIDEO":
        _validate_declared_type(detected, filename, content_type)
        validate_video_before_reencoding(content, max_bytes=max_bytes)
        content = process_video_upload(content, max_bytes=max_bytes)
    return sanitize_media_upload(content, filename=filename, content_type=content_type, max_bytes=max_bytes)

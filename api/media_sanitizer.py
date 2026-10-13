"""In-memory media validation and sanitization for draft uploads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from typing import Literal

from PIL import Image, ImageSequence, UnidentifiedImageError


MAX_IMAGE_PIXELS = 40_000_000
MAX_FILENAME_LENGTH = 120


class MediaSanitizerError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class MediaType:
    mime_type: str
    extension: str
    media_type: Literal["IMAGE", "VIDEO"]
    pil_format: str | None
    allowed_extensions: frozenset[str]
    allowed_content_types: frozenset[str]


@dataclass(frozen=True)
class SanitizedMedia:
    content: bytes
    mime_type: str
    extension: str
    media_type: Literal["IMAGE", "VIDEO"]
    safe_filename: str


JPEG = MediaType(
    mime_type="image/jpeg",
    extension=".jpg",
    media_type="IMAGE",
    pil_format="JPEG",
    allowed_extensions=frozenset({".jpg", ".jpeg"}),
    allowed_content_types=frozenset({"image/jpeg"}),
)
PNG = MediaType(
    mime_type="image/png",
    extension=".png",
    media_type="IMAGE",
    pil_format="PNG",
    allowed_extensions=frozenset({".png"}),
    allowed_content_types=frozenset({"image/png"}),
)
GIF = MediaType(
    mime_type="image/gif",
    extension=".gif",
    media_type="IMAGE",
    pil_format="GIF",
    allowed_extensions=frozenset({".gif"}),
    allowed_content_types=frozenset({"image/gif"}),
)
WEBP = MediaType(
    mime_type="image/webp",
    extension=".webp",
    media_type="IMAGE",
    pil_format="WEBP",
    allowed_extensions=frozenset({".webp"}),
    allowed_content_types=frozenset({"image/webp"}),
)
MP4 = MediaType(
    mime_type="video/mp4",
    extension=".mp4",
    media_type="VIDEO",
    pil_format=None,
    allowed_extensions=frozenset({".mp4"}),
    allowed_content_types=frozenset({"video/mp4"}),
)
MOV = MediaType(
    mime_type="video/quicktime",
    extension=".mov",
    media_type="VIDEO",
    pil_format=None,
    allowed_extensions=frozenset({".mov"}),
    allowed_content_types=frozenset({"video/quicktime"}),
)


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_ENCODED_CONTROL_CHARS_RE = re.compile(r"%(?:0[0-9a-fA-F]|1[0-9a-fA-F]|7[fF])")


def detect_media_type(content: bytes) -> MediaType:
    if content.startswith(b"\xff\xd8\xff"):
        return JPEG
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if content.startswith((b"GIF87a", b"GIF89a")):
        return GIF
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return WEBP
    if _looks_like_ftyp(content):
        return MOV if content[8:12] == b"qt  " else MP4
    raise MediaSanitizerError("tipo real desconhecido", status_code=415)


def sanitize_filename(filename: str | None, extension: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    name = (filename or "arquivo").replace("\\", "/").split("/")[-1]
    name = _ENCODED_CONTROL_CHARS_RE.sub("", name)
    name = _CONTROL_CHARS_RE.sub("", name).strip()
    stem = PurePath(name).stem
    stem = _CONTROL_CHARS_RE.sub("", stem).strip(" .") or "arquivo"
    available = max(1, max_length - len(extension))
    return f"{stem[:available]}{extension}"


def sanitize_media_upload(
    content: bytes,
    *,
    filename: str | None,
    content_type: str | None,
    max_bytes: int | None = None,
    max_pixels: int = MAX_IMAGE_PIXELS,
) -> SanitizedMedia:
    if max_bytes is not None and len(content) > max_bytes:
        raise MediaSanitizerError("arquivo excede o tamanho máximo")
    detected = detect_media_type(content)
    _validate_declared_type(detected, filename, content_type)
    if detected.media_type == "IMAGE":
        clean = _sanitize_image(content, detected, max_pixels)
    else:
        _validate_video_boxes(content, max_bytes=max_bytes)
        clean = content
    return SanitizedMedia(
        content=clean,
        mime_type=detected.mime_type,
        extension=detected.extension,
        media_type=detected.media_type,
        safe_filename=sanitize_filename(filename, detected.extension),
    )


def _validate_declared_type(detected: MediaType, filename: str | None, content_type: str | None) -> None:
    extension = PurePath((filename or "").replace("\\", "/").split("/")[-1]).suffix.lower()
    if extension not in detected.allowed_extensions:
        raise MediaSanitizerError("extensão incompatível com o conteúdo real", status_code=415)
    declared = (content_type or "").split(";", 1)[0].strip().lower()
    if declared not in detected.allowed_content_types:
        raise MediaSanitizerError("tipo informado incompatível com o conteúdo real", status_code=415)


def _sanitize_image(content: bytes, detected: MediaType, max_pixels: int) -> bytes:
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format != detected.pil_format:
                raise MediaSanitizerError("imagem incompatível com o tipo real")
            if image.width * image.height > max_pixels:
                raise MediaSanitizerError("dimensões da imagem excedem o limite")
            if detected is GIF:
                return _sanitize_gif(image, max_pixels)
            image.load()
            return _encode_clean_image(image, detected)
    except MediaSanitizerError:
        raise
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise MediaSanitizerError("imagem inválida ou corrompida") from exc


def _encode_clean_image(image: Image.Image, detected: MediaType) -> bytes:
    output = BytesIO()
    clean = image.copy()
    if detected is JPEG and clean.mode not in ("RGB", "L"):
        clean = clean.convert("RGB")
    save_kwargs = {"format": detected.pil_format}
    if detected is JPEG:
        save_kwargs.update(quality=95, optimize=True)
    elif detected is PNG:
        save_kwargs.update(optimize=True)
    elif detected is WEBP:
        save_kwargs.update(quality=95, method=6)
    clean.save(output, **save_kwargs)
    return output.getvalue()


def _sanitize_gif(image: Image.Image, max_pixels: int) -> bytes:
    frames: list[Image.Image] = []
    durations: list[int] = []
    loop = int(image.info.get("loop", 0) or 0)
    for frame in ImageSequence.Iterator(image):
        if frame.width * frame.height > max_pixels:
            raise MediaSanitizerError("dimensões da imagem excedem o limite")
        frame.load()
        frames.append(frame.copy())
        durations.append(int(frame.info.get("duration", image.info.get("duration", 0)) or 0))
    if not frames:
        raise MediaSanitizerError("GIF sem quadros válidos")

    output = BytesIO()
    first, rest = frames[0], frames[1:]
    duration: int | list[int] = durations if rest else durations[0]
    first.save(
        output,
        format="GIF",
        save_all=bool(rest),
        append_images=rest,
        duration=duration,
        loop=loop,
    )
    return output.getvalue()


def _looks_like_ftyp(content: bytes) -> bool:
    if len(content) < 16 or content[4:8] != b"ftyp":
        return False
    size = int.from_bytes(content[:4], "big")
    return size >= 16 and size <= len(content)


def _validate_video_boxes(content: bytes, *, max_bytes: int | None = None) -> None:
    if max_bytes is not None and len(content) > max_bytes:
        raise MediaSanitizerError("vídeo excede o tamanho máximo")
    if not _looks_like_ftyp(content):
        raise MediaSanitizerError("vídeo inválido: caixa ftyp ausente")
    try:
        boxes = list(_iter_mp4_boxes(content, 0, len(content)))
    except ValueError as exc:
        raise MediaSanitizerError("vídeo inválido: estrutura inconsistente") from exc
    if not boxes or boxes[0][2] != b"ftyp":
        raise MediaSanitizerError("vídeo inválido: caixa ftyp deve ser a primeira")


def _iter_mp4_boxes(content: bytes, start: int, end: int):
    offset = start
    while offset < end:
        if end - offset < 8:
            raise ValueError("trailing bytes")
        size = int.from_bytes(content[offset:offset + 4], "big")
        kind = content[offset + 4:offset + 8]
        header = 8
        if size == 1:
            if end - offset < 16:
                raise ValueError("missing largesize")
            size = int.from_bytes(content[offset + 8:offset + 16], "big")
            header = 16
        elif size == 0:
            size = end - offset
        if size < header or offset + size > end:
            raise ValueError("invalid box size")
        yield offset, size, kind
        offset += size
    if offset != end:
        raise ValueError("unconsumed bytes")

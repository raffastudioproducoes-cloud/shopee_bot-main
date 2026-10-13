from io import BytesIO

import pytest
from PIL import Image

from api.media_sanitizer import MediaSanitizerError, sanitize_media_upload


def _image_bytes(fmt: str, mode: str = "RGB", color: str = "red", **save_kwargs):
    buf = BytesIO()
    Image.new(mode, (2, 2), color).save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()


def _mp4_bytes(extra: bytes = b""):
    def box(kind: bytes, payload: bytes = b"") -> bytes:
        return (len(payload) + 8).to_bytes(4, "big") + kind + payload

    return box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2mp41") + box(b"mdat") + extra


def _gps_exif_bytes():
    gps_ifd = (
        b"\x00\x01"
        + b"\x00\x01\x00\x02\x00\x00\x00\x02N\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )
    tiff = (
        b"MM\x00*\x00\x00\x00\x08"
        + b"\x00\x01"
        + b"\x88\x25\x00\x04\x00\x00\x00\x01\x00\x00\x00\x1a"
        + b"\x00\x00\x00\x00"
        + gps_ifd
    )
    return b"Exif\x00\x00" + tiff


def _mov_bytes():
    def box(kind: bytes, payload: bytes = b"") -> bytes:
        return (len(payload) + 8).to_bytes(4, "big") + kind + payload

    return box(b"ftyp", b"qt  \x00\x00\x00\x00qt  ") + box(b"mdat")


def test_jpeg_polyglot_is_reencoded_without_appended_payload():
    raw = _image_bytes("JPEG") + b"<script>x</script><?php evil(); ?>DROP TABLE posts"

    media = sanitize_media_upload(raw, filename="foto.jpg", content_type="image/jpeg")

    assert media.mime_type == "image/jpeg"
    assert media.extension == ".jpg"
    assert b"<script" not in media.content
    assert b"<?php" not in media.content
    assert b"DROP TABLE" not in media.content
    assert len(media.content) < len(raw)
    Image.open(BytesIO(media.content)).verify()


def test_exif_gps_is_stripped_from_jpeg():
    raw = _image_bytes("JPEG", exif=_gps_exif_bytes())
    assert 0x8825 in Image.open(BytesIO(raw)).getexif()

    media = sanitize_media_upload(raw, filename="foto.jpeg", content_type="image/jpeg")

    assert 0x8825 not in Image.open(BytesIO(media.content)).getexif()


@pytest.mark.parametrize(("filename", "content_type", "content"), [
    ("a.png", "image/png", _image_bytes("PNG", mode="RGBA", color="blue")),
    ("a.gif", "image/gif", _image_bytes("GIF", mode="P", color=1)),
    ("a.webp", "image/webp", _image_bytes("WEBP", color="green")),
    ("a.mp4", "video/mp4", _mp4_bytes()),
    ("a.mov", "video/quicktime", _mov_bytes()),
])
def test_supported_media_types_pass(filename, content_type, content):
    media = sanitize_media_upload(content, filename=filename, content_type=content_type)

    assert media.content
    assert media.safe_filename.startswith("a.")


def test_wrong_extension_is_rejected():
    with pytest.raises(MediaSanitizerError, match="extensão"):
        sanitize_media_upload(_image_bytes("JPEG"), filename="foto.png", content_type="image/png")


def test_truncated_image_is_rejected():
    with pytest.raises(MediaSanitizerError, match="imagem"):
        sanitize_media_upload(_image_bytes("JPEG")[:16], filename="foto.jpg", content_type="image/jpeg")


def test_huge_dimension_image_is_rejected_by_pixel_guard():
    with pytest.raises(MediaSanitizerError, match="dimensões"):
        sanitize_media_upload(_image_bytes("PNG"), filename="foto.png", content_type="image/png", max_pixels=1)


def test_non_media_is_rejected():
    with pytest.raises(MediaSanitizerError, match="tipo"):
        sanitize_media_upload(b"nao sou midia", filename="nota.txt", content_type="text/plain")


def test_video_trailing_garbage_is_rejected():
    with pytest.raises(MediaSanitizerError, match="vídeo"):
        sanitize_media_upload(_mp4_bytes(b"garbage"), filename="video.mp4", content_type="video/mp4")


def test_filename_is_basename_without_controls_and_limited():
    media = sanitize_media_upload(
        _image_bytes("JPEG"),
        filename="../..\x00/evil\x01" + ("a" * 260) + ".jpg",
        content_type="image/jpeg",
    )

    assert "/" not in media.safe_filename
    assert "\\" not in media.safe_filename
    assert "\x01" not in media.safe_filename
    assert media.safe_filename.endswith(".jpg")
    assert len(media.safe_filename) <= 120


# ── metadados: comentário, ICC, XMP e EXIF não podem sobreviver ──────────────

_PAYLOAD = b"<script>alert(1)</script>"
_METADATA_KEYS = ("comment", "icc_profile", "exif", "xmp")


def _tainted(fmt: str) -> bytes:
    buf = BytesIO()
    im = Image.new("RGB", (4, 4), "red")
    if fmt == "JPEG":
        im.save(buf, "JPEG", comment=_PAYLOAD, icc_profile=_PAYLOAD, exif=_gps_exif_bytes())
    elif fmt == "PNG":
        im.save(buf, "PNG", icc_profile=_PAYLOAD, exif=_gps_exif_bytes())
    elif fmt == "WEBP":
        im.save(buf, "WEBP", icc_profile=_PAYLOAD, exif=_gps_exif_bytes(), xmp=_PAYLOAD)
    else:
        frames = [Image.new("RGB", (4, 4), c).convert("P") for c in ("red", "blue")]
        frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], comment=_PAYLOAD)
    return buf.getvalue()


@pytest.mark.parametrize(("fmt", "name", "ctype"), [
    ("JPEG", "a.jpg", "image/jpeg"),
    ("PNG", "a.png", "image/png"),
    ("WEBP", "a.webp", "image/webp"),
    ("GIF", "a.gif", "image/gif"),
])
def test_metadata_does_not_survive_reencoding(fmt, name, ctype):
    raw = _tainted(fmt)
    assert [k for k in _METADATA_KEYS if k in Image.open(BytesIO(raw)).info]

    out = sanitize_media_upload(raw, filename=name, content_type=ctype).content

    info = Image.open(BytesIO(out)).info
    assert not [k for k in _METADATA_KEYS if k in info]
    assert b"<script>" not in out


def test_animated_gif_frames_survive_metadata_strip():
    raw = _tainted("GIF")
    out = sanitize_media_upload(raw, filename="a.gif", content_type="image/gif").content
    assert Image.open(BytesIO(out)).n_frames == 2


def test_exif_orientation_is_applied_before_exif_is_dropped():
    exif = Image.Exif()
    exif[0x0112] = 6  # rotaciona 90 graus
    buf = BytesIO()
    Image.new("RGB", (4, 2), "red").save(buf, "JPEG", exif=exif.tobytes())

    out = sanitize_media_upload(buf.getvalue(), filename="a.jpg", content_type="image/jpeg").content

    result = Image.open(BytesIO(out))
    assert result.size == (2, 4)
    assert 0x0112 not in result.getexif()


# ── orçamento de pixels/quadros e exceções inesperadas ───────────────────────

import struct
import time
import zlib


def _gif_bytes(frame_count: int, size: tuple[int, int]) -> bytes:
    a, b = Image.new("P", size, 0), Image.new("P", size, 0)
    for im in (a, b):
        im.putpalette([0, 0, 0, 255, 0, 0])
    b.putpixel((0, 0), 1)
    frames = [a if i % 2 == 0 else b for i in range(frame_count)]
    buf = BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:])
    return buf.getvalue()


def test_gif_with_total_pixel_budget_exceeded_is_rejected_fast():
    raw = _gif_bytes(31, (1000, 1000))
    assert len(raw) < 200_000

    started = time.monotonic()
    with pytest.raises(MediaSanitizerError, match="dimensões"):
        sanitize_media_upload(raw, filename="a.gif", content_type="image/gif")
    assert time.monotonic() - started < 2


def test_animation_with_too_many_frames_is_rejected():
    with pytest.raises(MediaSanitizerError, match="quadros"):
        sanitize_media_upload(_gif_bytes(201, (2, 2)), filename="a.gif", content_type="image/gif")


def test_small_animation_within_budget_passes():
    media = sanitize_media_upload(_gif_bytes(10, (8, 8)), filename="a.gif", content_type="image/gif")
    assert Image.open(BytesIO(media.content)).n_frames == 10


def test_animated_webp_budget_is_checked_before_decoding():
    frames = [Image.new("RGB", (3000, 3000), c) for c in ("red", "blue")] * 8
    buf = BytesIO()
    frames[0].save(buf, "WEBP", save_all=True, append_images=frames[1:], lossless=True)

    with pytest.raises(MediaSanitizerError, match="dimensões"):
        sanitize_media_upload(buf.getvalue(), filename="a.webp", content_type="image/webp")


def _png_with_ihdr_size(width: int, height: int) -> bytes:
    raw = bytearray(_image_bytes("PNG"))
    ihdr = struct.pack(">II", width, height) + bytes(raw[16 + 8:16 + 13])
    raw[16:24] = ihdr[:8]
    raw[29:33] = struct.pack(">I", zlib.crc32(b"IHDR" + bytes(raw[16:29])))
    return bytes(raw)


def test_decompression_bomb_is_a_sanitizer_error_not_a_500():
    raw = _png_with_ihdr_size(60_000, 60_000)

    with pytest.raises(MediaSanitizerError, match="dimensões"):
        sanitize_media_upload(raw, filename="a.png", content_type="image/png")


@pytest.mark.parametrize("exc", [SyntaxError("x"), EOFError("x"), struct.error("x"), RuntimeError("x")])
def test_unexpected_decoder_errors_become_sanitizer_error(monkeypatch, exc):
    from api import media_sanitizer

    def boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(media_sanitizer.Image, "open", boom)

    with pytest.raises(MediaSanitizerError, match="imagem inválida") as info:
        sanitize_media_upload(_image_bytes("PNG"), filename="a.png", content_type="image/png")
    assert str(info.value) == "imagem inválida ou corrompida"

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

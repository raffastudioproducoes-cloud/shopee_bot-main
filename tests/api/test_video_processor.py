"""Untrusted MP4 must be decoded and rebuilt before it reaches Storage."""

import shutil
import subprocess

import pytest

from api.media_sanitizer import MediaSanitizerError
from api.video_processor import process_video_upload


@pytest.fixture
def short_video(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg and shutil.which("ffprobe"), "ffmpeg e ffprobe sao necessarios para testar video"
    path = tmp_path / "source.mp4"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=32x32:d=0.5",
         "-metadata", "comment=PRIVATE_TEST_MARKER", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
        check=True, timeout=15,
    )
    return path.read_bytes()


def test_video_is_reencoded_without_input_metadata(short_video):
    assert b"PRIVATE_TEST_MARKER" in short_video
    clean = process_video_upload(short_video, max_bytes=50 * 1024 * 1024)
    assert clean != short_video
    assert b"PRIVATE_TEST_MARKER" not in clean
    assert clean[4:8] == b"ftyp"


def test_structural_mp4_without_decodable_video_fails_closed():
    raw = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2\x00\x00\x00\x08mdat"
    with pytest.raises(MediaSanitizerError):
        process_video_upload(raw, max_bytes=50 * 1024 * 1024)


def test_missing_tools_fails_closed(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(MediaSanitizerError) as exc:
        process_video_upload(b"fake", max_bytes=100)
    assert exc.value.status_code == 503


def test_probe_limits_dimensions_and_duration(monkeypatch, short_video):
    from api import video_processor

    def fake_probe(*_args, **_kwargs):
        return {"streams": [{"width": 9000, "height": 9000}], "format": {"duration": "1.0"}}

    monkeypatch.setattr(video_processor, "_probe_video", fake_probe)
    with pytest.raises(MediaSanitizerError, match="dimensões"):
        process_video_upload(short_video, max_bytes=50 * 1024 * 1024)

    monkeypatch.setattr(video_processor, "_probe_video", lambda *_args, **_kwargs: {"streams": [{"width": 32, "height": 32}], "format": {"duration": "601"}})
    with pytest.raises(MediaSanitizerError, match="duração"):
        process_video_upload(short_video, max_bytes=50 * 1024 * 1024)

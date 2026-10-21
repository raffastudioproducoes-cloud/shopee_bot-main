"""Rebuild an uploaded MP4 from decoded audio/video streams before storage."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from threading import BoundedSemaphore
from pathlib import Path

from .media_sanitizer import MediaSanitizerError, _validate_video_boxes

MAX_VIDEO_SECONDS = 600
MAX_VIDEO_DIMENSION = 4096
MAX_VIDEO_PIXELS = 16_000_000
PROBE_TIMEOUT_SECONDS = 10
TRANSCODE_TIMEOUT_SECONDS = 90
_VIDEO_SLOTS = BoundedSemaphore(2)


def _tool_env(directory: Path) -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(directory), "TMPDIR": str(directory)}
    if os.name == "nt" and os.environ.get("SystemRoot"):
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


def _probe_video(ffprobe: str, path: Path, directory: Path) -> dict:
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-protocol_whitelist", "file", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)],
            cwd=directory, env=_tool_env(directory), stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=PROBE_TIMEOUT_SECONDS, check=False,
        )
        if result.returncode or len(result.stdout) > 8192:
            raise MediaSanitizerError("vídeo inválido ou não decodificável")
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, OSError, ValueError, TypeError) as exc:
        raise MediaSanitizerError("vídeo inválido ou não decodificável") from exc


def _video_properties(probe: dict) -> float:
    try:
        stream = probe["streams"][0]
        width, height = int(stream["width"]), int(stream["height"])
        duration = float(probe["format"]["duration"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MediaSanitizerError("vídeo sem duração ou faixa visual válida") from exc
    if width <= 0 or height <= 0 or width > MAX_VIDEO_DIMENSION or height > MAX_VIDEO_DIMENSION or width * height > MAX_VIDEO_PIXELS:
        raise MediaSanitizerError("dimensões do vídeo excedem o limite")
    if not math.isfinite(duration) or duration <= 0 or duration > MAX_VIDEO_SECONDS:
        raise MediaSanitizerError("duração do vídeo excede o limite")
    return duration


def process_video_upload(content: bytes | bytearray, *, max_bytes: int) -> bytes:
    """Reject on tool failure; never store the original user-supplied MP4 bytes."""
    if not _VIDEO_SLOTS.acquire(blocking=False):
        raise MediaSanitizerError("processamento de vídeo ocupado; tente novamente", status_code=429)
    try:
        return _process_video_upload(content, max_bytes=max_bytes)
    finally:
        _VIDEO_SLOTS.release()


def _process_video_upload(content: bytes | bytearray, *, max_bytes: int) -> bytes:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise MediaSanitizerError("processamento de vídeo indisponível", status_code=503)
    if len(content) > max_bytes:
        raise MediaSanitizerError("vídeo excede o tamanho máximo")
    try:
        return _process_in_temporary_directory(content, max_bytes, ffmpeg, ffprobe)
    except OSError as exc:
        raise MediaSanitizerError("processamento de vídeo indisponível", status_code=503) from exc


def _process_in_temporary_directory(content: bytes | bytearray, max_bytes: int, ffmpeg: str, ffprobe: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="post-video-") as temporary:
        directory = Path(temporary)
        source, output = directory / "input.mp4", directory / "clean.mp4"
        source.write_bytes(content)
        duration = _video_properties(_probe_video(ffprobe, source, directory))
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-xerror",
            "-threads", "1", "-filter_threads", "1", "-protocol_whitelist", "file",
            "-i", str(source), "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn",
            "-map_metadata", "-1", "-map_metadata:s", "-1", "-map_chapters", "-1", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            "-fs", str(max_bytes + 1), "-y", str(output),
        ]
        try:
            result = subprocess.run(
                command, cwd=directory, env=_tool_env(directory), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=TRANSCODE_TIMEOUT_SECONDS, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MediaSanitizerError("vídeo excede o tempo de processamento") from exc
        except OSError as exc:
            raise MediaSanitizerError("processamento de vídeo indisponível", status_code=503) from exc
        if result.returncode or not output.exists() or not output.stat().st_size or output.stat().st_size > max_bytes:
            raise MediaSanitizerError("vídeo não pôde ser convertido dentro dos limites")
        clean_duration = _video_properties(_probe_video(ffprobe, output, directory))
        if clean_duration + max(0.5, duration * 0.02) < duration:
            raise MediaSanitizerError("vídeo excede o tamanho máximo após conversão")
        clean = output.read_bytes()
        _validate_video_boxes(clean, max_bytes=max_bytes)
        return clean

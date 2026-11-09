import os
import tempfile
from types import SimpleNamespace

import pytest

from shopee_bot.apis import tiktok as api


def test_upload_chunk_plan_handles_small_and_large_files():
    mb = 1024 * 1024
    assert api._upload_chunk_plan(4 * mb) == (4 * mb, 1)
    chunk_size, count = api._upload_chunk_plan(65 * mb)
    assert count == 2
    assert chunk_size <= api.MAX_CHUNK_BYTES
    assert chunk_size >= api.MIN_CHUNK_BYTES
    chunk_size, count = api._upload_chunk_plan(4 * 1024 * mb)
    assert count == 64
    assert chunk_size == 64 * mb


def test_upload_chunk_plan_rejects_files_over_four_gb():
    with pytest.raises(api.TikTokAPIError, match="4 GB"):
        api._upload_chunk_plan(api.MAX_VIDEO_BYTES + 1)


def test_init_video_post_sends_chunk_metadata(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""
        def json(self):
            return {"data": {"publish_id": "pub", "upload_url": "https://upload.test"}}

    def fake_retry(func, url, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr(api, "retry_with_backoff", fake_retry)
    publish_id, upload_url = api._init_video_post("token", 65 * 1024 * 1024, "caption", "SELF_ONLY")
    assert publish_id == "pub"
    assert upload_url == "https://upload.test"
    assert captured["source_info"]["total_chunk_count"] == 2
    assert captured["source_info"]["chunk_size"] <= api.MAX_CHUNK_BYTES


def test_upload_video_file_sends_sequential_ranges(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "MAX_CHUNK_BYTES", 6)
    monkeypatch.setattr(api, "MIN_CHUNK_BYTES", 5)
    video = tmp_path / "video.mp4"
    video.write_bytes(b"abcdefghijk")
    calls = []

    def fake_put(url, data, headers):
        calls.append((bytes(data), headers))
        return SimpleNamespace(status_code=206 if len(calls) == 1 else 201, text="")

    monkeypatch.setattr(api.requests, "put", fake_put)
    api._upload_video_file("https://upload.test", str(video))
    assert [c[0] for c in calls] == [b"abcdef", b"ghijk"]
    assert calls[0][1]["Content-Range"] == "bytes 0-5/11"
    assert calls[1][1]["Content-Range"] == "bytes 6-10/11"


def test_post_video_blocks_duration_above_creator_limit(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")
    monkeypatch.setattr(api, "get_creator_info", lambda token: {
        "max_video_post_duration_sec": 180,
        "privacy_level_options": ["SELF_ONLY"],
    })
    monkeypatch.setattr(api, "_video_duration_seconds", lambda path: 181.0)
    monkeypatch.setattr(api, "_init_video_post", lambda *a: (_ for _ in ()).throw(AssertionError("upload não deve iniciar")))
    with pytest.raises(api.TikTokAPIError, match="permite no máximo 180s"):
        api.post_video("token", str(video), "caption")


def test_post_video_blocks_unavailable_privacy_option(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")
    monkeypatch.setattr(api, "get_creator_info", lambda token: {
        "max_video_post_duration_sec": 300,
        "privacy_level_options": ["PUBLIC_TO_EVERYONE"],
    })
    monkeypatch.setattr(api, "_video_duration_seconds", lambda path: 120.0)
    monkeypatch.setattr(api, "_init_video_post", lambda *a: (_ for _ in ()).throw(AssertionError("upload não deve iniciar")))
    with pytest.raises(api.TikTokAPIError, match="privacidade"):
        api.post_video("token", str(video), "caption")

import os
import tempfile
from types import SimpleNamespace

import pytest

from shopee_bot.apis import tiktok as api
from shopee_bot.api.tiktok_options import TikTokPostOptions
from shopee_bot.utils import was_not_published


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


class _Response:
    status_code = 200
    text = ""

    def __init__(self, body=None):
        self._body = body or {"data": {"publish_id": "pub", "upload_url": "https://upload.test"},
                              "error": {"code": "ok"}}

    def json(self):
        return self._body


def _options(**overrides):
    return TikTokPostOptions.model_validate({
        "mode": "direct", "privacy_level": "SELF_ONLY", "consent": True, **overrides,
    })


def test_init_video_post_sends_chunk_metadata(monkeypatch):
    captured = {}

    def fake_retry(func, url, **kwargs):
        captured["url"] = url
        captured.update(kwargs["json"])
        return _Response()

    monkeypatch.setattr(api, "retry_with_backoff", fake_retry)
    publish_id, upload_url = api._init_video_post(
        "token", 65 * 1024 * 1024, {"title": "caption", "privacy_level": "SELF_ONLY"},
    )
    assert publish_id == "pub"
    assert upload_url == "https://upload.test"
    assert captured["url"] == api.POST_INIT_URL
    assert captured["post_info"] == {"title": "caption", "privacy_level": "SELF_ONLY"}
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


CREATOR = {
    "creator_nickname": "Loja da Ana",
    "max_video_post_duration_sec": 300,
    "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
    "comment_disabled": False, "duet_disabled": False, "stitch_disabled": False,
}


def _no_init(*a, **k):
    raise AssertionError("upload não deve iniciar")


def test_post_video_blocks_duration_above_creator_limit(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")
    monkeypatch.setattr(api, "get_creator_info", lambda token: {**CREATOR, "max_video_post_duration_sec": 180})
    monkeypatch.setattr(api, "_video_duration_seconds", lambda path: 181.0)
    monkeypatch.setattr(api, "_init_video_post", _no_init)
    with pytest.raises(api.TikTokAPIError, match="permite no máximo 180s"):
        api.post_video("token", str(video), "caption", _options())


def test_post_video_blocks_unavailable_privacy_option(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")
    monkeypatch.setattr(api, "get_creator_info", lambda token: {**CREATOR, "privacy_level_options": ["SELF_ONLY"]})
    monkeypatch.setattr(api, "_video_duration_seconds", lambda path: 120.0)
    monkeypatch.setattr(api, "_init_video_post", _no_init)
    with pytest.raises(api.TikTokAPIError, match="privacidade"):
        api.post_video("token", str(video), "caption", _options(privacy_level="PUBLIC_TO_EVERYONE"))


def test_post_video_sends_exactly_the_user_choice(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")
    sent, order = {}, []
    monkeypatch.setattr(api, "get_creator_info", lambda token: CREATOR)
    monkeypatch.setattr(api, "_video_duration_seconds", lambda path: 30.0)
    monkeypatch.setattr(api, "_init_video_post",
                        lambda token, size, info: order.append("init") or sent.update(info) or ("pub", "u"))
    monkeypatch.setattr(api, "_upload_video_file", lambda url, path: order.append("upload"))
    monkeypatch.setattr(api, "_wait_publish_complete", lambda token, pid: order.append("status"))
    options = _options(privacy_level="MUTUAL_FOLLOW_FRIENDS", allow_comment=True,
                       commercial_content=True, brand_organic=True, brand_content=True, is_aigc=True)
    assert api.post_video("token", str(video), "minha legenda", options,
                          before_publish=lambda: order.append("boundary")) == "pub"
    assert order == ["boundary", "init", "upload", "status"]
    assert sent == {
        "title": "minha legenda", "privacy_level": "MUTUAL_FOLLOW_FRIENDS",
        "disable_comment": False, "disable_duet": True, "disable_stitch": True,
        "brand_content_toggle": True, "brand_organic_toggle": True, "is_aigc": True,
    }


def test_post_video_blocks_interaction_disabled_by_creator(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")
    monkeypatch.setattr(api, "get_creator_info", lambda token: {**CREATOR, "duet_disabled": True})
    monkeypatch.setattr(api, "_video_duration_seconds", lambda path: 30.0)
    monkeypatch.setattr(api, "_init_video_post", _no_init)
    with pytest.raises(api.TikTokAPIError, match="Duet"):
        api.post_video("token", str(video), "x", _options(allow_duet=True))


@pytest.mark.parametrize("code, message", [
    ("spam_risk_too_many_posts", "limite diário"),
    ("spam_risk_user_banned_from_posting", "impedida"),
    ("reached_active_user_cap", "cota diária"),
])
def test_creator_info_error_code_with_http_200_blocks(monkeypatch, code, message):
    monkeypatch.setattr(api, "retry_with_backoff",
                        lambda *a, **k: _Response({"data": {}, "error": {"code": code}}))
    with pytest.raises(api.TikTokAPIError, match=message):
        api.get_creator_info("token")


def test_post_video_blocks_when_creator_cannot_post(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")

    def cannot(token):
        raise api.TikTokAPIError("Esta conta TikTok atingiu o limite diário de publicações.")

    monkeypatch.setattr(api, "get_creator_info", cannot)
    monkeypatch.setattr(api, "_init_video_post", _no_init)
    with pytest.raises(api.TikTokAPIError, match="limite diário") as err:
        api.post_video("token", str(video), "caption", _options())
    assert was_not_published(err.value)


def test_draft_upload_uses_inbox_endpoint_without_post_info(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"123")
    captured, statuses = {}, iter(["PROCESSING_UPLOAD", "SEND_TO_USER_INBOX"])

    def fake_retry(func, url, **kwargs):
        if url == api.POST_STATUS_URL:
            return _Response({"data": {"status": next(statuses)}, "error": {"code": "ok"}})
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _Response()

    monkeypatch.setattr(api, "retry_with_backoff", fake_retry)
    monkeypatch.setattr(api, "_upload_video_file", lambda url, path: None)
    monkeypatch.setattr(api.time, "sleep", lambda s: None)
    assert api.upload_video_draft("token", str(video)) == "pub"
    assert captured["url"] == api.INBOX_INIT_URL
    assert "post_info" not in captured["json"]
    assert captured["json"]["source_info"]["source"] == "FILE_UPLOAD"
    assert captured["json"]["source_info"]["video_size"] == 3

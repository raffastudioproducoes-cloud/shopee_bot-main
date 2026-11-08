"""Posters are private, account-scoped and regenerated once for legacy MP4s."""
import asyncio
import uuid
from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from api.routers import product_media

ASSET = uuid.UUID("11111111-1111-4111-8111-111111111111")
VIDEO = {
    "id": str(ASSET), "product_id": 12, "status": "ready", "media_type": "VIDEO",
    "storage_key": f"products/owner/12/{ASSET}.mp4",
}


class FakeStorage:
    def __init__(self):
        self.assets = {VIDEO["storage_key"]: b"pretend-sanitized-video"}
        self.uploads = []

    def from_(self, name):
        assert name == "post-media"
        return self

    def download(self, key):
        if key not in self.assets:
            raise FileNotFoundError(key)
        return self.assets[key]

    def upload(self, key, data, options):
        self.uploads.append(key)
        self.assets[key] = data


@contextmanager
def capacity(_size):
    yield


async def inline(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def test_legacy_video_gets_private_real_frame_cached_once(monkeypatch):
    fake = FakeStorage()
    monkeypatch.setattr(product_media, "supabase", fake)
    monkeypatch.setattr(product_media, "_owned_asset", lambda *_: VIDEO)
    monkeypatch.setattr(product_media, "run_in_threadpool", inline)
    monkeypatch.setattr(product_media, "storage_upload_reservation", capacity)
    extracted = []
    def poster(content):
        extracted.append(content)
        return b"\xff\xd8thumbnail\xff\xd9"
    monkeypatch.setattr(product_media, "generate_video_thumbnail", poster)
    first = asyncio.run(product_media.product_video_thumbnail(12, ASSET, user_id="owner"))
    second = asyncio.run(product_media.product_video_thumbnail(12, ASSET, user_id="owner"))
    assert first.body == second.body == b"\xff\xd8thumbnail\xff\xd9"
    assert first.media_type == "image/jpeg"
    assert first.headers["cache-control"].startswith("private")
    assert len(extracted) == len(fake.uploads) == 1
    assert fake.uploads[0].endswith(".poster.jpg")


def test_thumbnail_rejects_nonvideo_and_untrusted_storage_key(monkeypatch):
    monkeypatch.setattr(product_media, "_owned_asset", lambda *_: {**VIDEO, "media_type": "IMAGE"})
    with pytest.raises(HTTPException) as nonvideo:
        asyncio.run(product_media.product_video_thumbnail(12, ASSET, user_id="owner"))
    assert nonvideo.value.status_code == 404
    monkeypatch.setattr(product_media, "_owned_asset", lambda *_: {
        **VIDEO, "storage_key": f"products/other/12/{ASSET}.mp4"})
    with pytest.raises(HTTPException) as wrong_key:
        asyncio.run(product_media.product_video_thumbnail(12, ASSET, user_id="owner"))
    assert wrong_key.value.status_code == 409

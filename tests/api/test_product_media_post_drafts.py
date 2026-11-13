"""Mídias cadastradas em Produtos viram rascunhos privados do post (cópia no Storage).

Sem rede social nem Storage real: o Storage é um gravador em memória.
"""
from contextlib import nullcontext

from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id

ASSET = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
VIDEO = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


class _Storage:
    def __init__(self, fail=False):
        self.copies, self.removed, self.fail = [], [], fail

    def from_(self, _bucket):
        return self

    def copy(self, origin, target):
        if self.fail:
            raise RuntimeError("storage down")
        self.copies.append((origin, target))

    def remove(self, keys):
        self.removed.append(keys)


def _asset(asset_id=ASSET, **over):
    row = {
        "id": asset_id, "user_id": 42, "product_id": 7, "media_type": "IMAGE", "slot": 1,
        "file_name": "foto.jpg", "mime_type": "image/jpeg", "size_bytes": 1234,
        "storage_key": f"products/42/7/{asset_id}.jpg", "status": "ready",
    }
    return {**row, **over}


def _client(fake_db, monkeypatch, media, storage=None, profile_id="profile-a"):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: profile_id
    db = fake_db({
        "temporary_media_uploads": [],
        "products": [{"id": 7, "user_id": 42, "profile_id": None}, {"id": 8, "user_id": 99, "profile_id": None}],
        "product_media": media,
    })
    db.storage = storage or _Storage()
    monkeypatch.setattr(posts_module, "supabase", db)
    monkeypatch.setattr(posts_module, "cleanup_expired_media_drafts", lambda: None)
    monkeypatch.setattr(posts_module, "storage_upload_reservation", lambda size: nullcontext())
    return TestClient(app), db


def test_product_image_and_video_are_copied_to_profile_draft(fake_db, monkeypatch):
    video = _asset(VIDEO, media_type="VIDEO", mime_type="video/mp4", file_name="demo.mp4",
                   storage_key=f"products/42/7/{VIDEO}.mp4")
    client, db = _client(fake_db, monkeypatch, [_asset(), video])
    for asset_id, kind in ((ASSET, "IMAGE"), (VIDEO, "VIDEO")):
        res = client.post(f"/posts/product-media-drafts/7/{asset_id}")
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["status"] == "ready" and body["media_type"] == kind and body["profile_id"] == "profile-a"
        assert "storage_key" not in body
    drafts = db.tables["temporary_media_uploads"]
    assert [d["storage_key"].split("/")[:3] for d in drafts] == [["drafts", "42", "profile-a"]] * 2
    assert [origin for origin, _ in db.storage.copies] == [f"products/42/7/{ASSET}.jpg", f"products/42/7/{VIDEO}.mp4"]
    assert drafts[1]["storage_key"].endswith(".mp4")
    # A galeria do produto continua intacta.
    assert len(db.tables["product_media"]) == 2 and db.storage.removed == []


def test_foreign_product_or_asset_is_rejected_without_copy(fake_db, monkeypatch):
    foreign = _asset(user_id=99, product_id=8, storage_key=f"products/99/8/{ASSET}.jpg")
    client, db = _client(fake_db, monkeypatch, [foreign])
    assert client.post(f"/posts/product-media-drafts/8/{ASSET}").status_code == 404  # produto de outra conta
    assert client.post(f"/posts/product-media-drafts/7/{ASSET}").status_code == 404  # mídia de outro produto
    assert db.storage.copies == [] and db.tables["temporary_media_uploads"] == []


def test_unready_or_tampered_asset_is_rejected(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch, [_asset(status="uploading")])
    assert client.post(f"/posts/product-media-drafts/7/{ASSET}").status_code == 404
    db.tables["product_media"] = [_asset(storage_key=f"products/99/8/{ASSET}.jpg")]
    assert client.post(f"/posts/product-media-drafts/7/{ASSET}").status_code == 409
    db.tables["product_media"] = [_asset(storage_key=f"products/42/7/{ASSET}.html")]
    assert client.post(f"/posts/product-media-drafts/7/{ASSET}").status_code == 409
    db.tables["product_media"] = [_asset(size_bytes=51 * 1024 * 1024)]
    assert client.post(f"/posts/product-media-drafts/7/{ASSET}").status_code == 409
    assert client.post("/posts/product-media-drafts/7/nao-uuid").status_code == 422
    assert db.storage.copies == [] and db.tables["temporary_media_uploads"] == []


def test_storage_failure_leaves_no_draft(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch, [_asset()], storage=_Storage(fail=True))
    res = client.post(f"/posts/product-media-drafts/7/{ASSET}")
    assert res.status_code == 502
    assert db.tables["temporary_media_uploads"] == []


def test_requires_active_profile(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch, [_asset()], profile_id=None)
    assert client.post(f"/posts/product-media-drafts/7/{ASSET}").status_code in (400, 403, 409, 422)
    assert db.storage.copies == []

"""Rascunhos duraveis de mídia: propriedade por perfil e limpeza segura."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


def _client(fake_db, monkeypatch, profile_id="profile-a"):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: profile_id
    db = fake_db({"temporary_media_uploads": []})
    db.storage = MagicMock()
    monkeypatch.setattr(posts_module, "supabase", db)
    monkeypatch.setattr(posts_module, "cleanup_expired_media_drafts", lambda: None)
    return TestClient(app), db


def _jpeg():
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 32


def test_upload_draft_is_private_and_scoped_to_active_profile(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)

    response = client.post(
        "/posts/media-drafts",
        files={"file": ("oferta.jpg", _jpeg(), "image/jpeg")},
    )

    assert response.status_code == 201
    draft = response.json()
    assert draft["status"] == "ready"
    assert draft["profile_id"] == "profile-a"
    assert "storage_key" not in draft
    assert db.tables["temporary_media_uploads"][0]["user_id"] == 42
    assert db.tables["temporary_media_uploads"][0]["profile_id"] == "profile-a"
    assert db.tables["temporary_media_uploads"][0]["storage_bucket"] == "post-media"
    db.storage.from_.assert_called_with("post-media")
    db.storage.from_.return_value.upload.assert_called_once()


def test_delete_draft_refuses_other_profile_and_never_touches_storage(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch, profile_id="profile-b")
    db.tables["temporary_media_uploads"].append({
        "id": "7",
        "user_id": 42,
        "profile_id": "profile-a",
        "status": "ready",
        "storage_bucket": "post-media",
        "storage_key": "drafts/42/profile-a/a.jpg",
    })

    response = client.delete("/posts/media-drafts/7")

    assert response.status_code == 404
    db.storage.from_.assert_not_called()
    assert db.tables["temporary_media_uploads"][0]["id"] == "7"


def test_expired_cleanup_deletes_only_expired_drafts(fake_db, monkeypatch):
    db = fake_db({
        "temporary_media_uploads": [
            {
                "id": "1", "user_id": 42, "profile_id": "profile-a", "status": "ready",
                "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/remove.jpg",
                "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            },
            {
                "id": "2", "user_id": 42, "profile_id": "profile-a", "status": "ready",
                "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/live.jpg",
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
            },
        ],
    })
    db.storage = MagicMock()
    monkeypatch.setattr(posts_module, "supabase", db)

    removed = posts_module.cleanup_expired_media_drafts(now=datetime.now(timezone.utc))

    assert removed == 1
    assert [row["id"] for row in db.tables["temporary_media_uploads"]] == ["2"]
    db.storage.from_.return_value.remove.assert_called_once_with(["drafts/42/profile-a/remove.jpg"])


def _batch_body():
    return {
        "compositions": [
            {"network": "threads", "texts": ["copy"]},
            {"network": "x", "texts": ["copy"]},
        ],
        "draft_media_ids": ["draft-1"],
        "schedule": {"trigger": "date", "run_date": "2030-01-01T10:00:00"},
    }


def _batch_client(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.tables["temporary_media_uploads"].append({
        "id": "draft-1", "user_id": 42, "profile_id": "profile-a", "status": "ready",
        "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/offer.jpg",
        "file_name": "offer.jpg", "size_bytes": 12, "media_type": "IMAGE",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    })

    async def fake_job(**_kwargs):
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    return client, db


def test_preview_is_read_only_and_shows_per_network_mode(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)

    response = client.post("/posts/preview", json=_batch_body())

    assert response.status_code == 200
    plans = {plan["network"]: plan for plan in response.json()["plans"]}
    assert plans["threads"]["mode"] == "single_image"
    assert plans["x"]["mode"] == "single_image"
    assert db.tables.get("posts", []) == []
    assert db.tables.get("medias", []) == []


def test_batch_creates_all_deliverable_networks_with_one_server_group(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)

    response = client.post("/posts/batch", json=_batch_body())

    assert response.status_code == 201
    payload = response.json()
    assert payload["group_id"]
    assert {row["network"] for row in payload["created"]} == {"threads", "x"}
    assert len(db.tables["medias"]) == 1
    assert db.tables["temporary_media_uploads"][0]["status"] == "consumed"


def test_batch_persists_display_order_in_received_draft_order(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    for name in ("zzz", "aaa", "mmm"):
        db.tables["temporary_media_uploads"].append({
            "id": f"d-{name}", "user_id": 42, "profile_id": "profile-a", "status": "ready",
            "storage_bucket": "post-media", "storage_key": f"drafts/{name}.jpg",
            "file_name": f"{name}.jpg", "size_bytes": 12, "media_type": "IMAGE",
            "expires_at": expires,
        })
    body = {
        "compositions": [{"network": "threads", "texts": ["copy"]}],
        "draft_media_ids": ["d-zzz", "d-aaa", "d-mmm"],
        "schedule": {"trigger": "date", "run_date": "2030-01-01T10:00:00"},
    }

    response = client.post("/posts/batch", json=body)

    assert response.status_code == 201
    names = {m["id"]: m["file_name"] for m in db.tables["medias"]}
    links = sorted(db.tables["posts_medias"], key=lambda r: r["display_order"])
    assert [r["display_order"] for r in links] == [0, 1, 2]
    assert [names[r["media_id"]] for r in links] == ["zzz.jpg", "aaa.jpg", "mmm.jpg"]

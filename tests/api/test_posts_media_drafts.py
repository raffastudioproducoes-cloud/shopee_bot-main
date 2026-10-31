"""Rascunhos duraveis de mídia: propriedade por perfil e limpeza segura."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest

from fastapi.testclient import TestClient
from PIL import Image

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


DRAFT_1 = "11111111-1111-4111-8111-111111111111"
D_ZZZ = "22222222-2222-4222-8222-222222222222"
D_AAA = "33333333-3333-4333-8333-333333333333"
D_MMM = "44444444-4444-4444-8444-444444444444"


def _client(fake_db, monkeypatch, profile_id="profile-a"):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: profile_id
    db = fake_db({"temporary_media_uploads": []})
    db.storage = MagicMock()
    monkeypatch.setattr(posts_module, "supabase", db)
    monkeypatch.setattr(posts_module, "cleanup_expired_media_drafts", lambda: None)
    return TestClient(app), db


def _jpeg():
    buf = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buf, format="JPEG")
    return buf.getvalue()


def _png():
    buf = BytesIO()
    Image.new("RGBA", (2, 2), "blue").save(buf, format="PNG")
    return buf.getvalue()


def _gif():
    buf = BytesIO()
    frames = [Image.new("P", (2, 2), color=i) for i in (1, 2)]
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=[10, 10], loop=0)
    return buf.getvalue()


def _webp():
    buf = BytesIO()
    Image.new("RGB", (2, 2), "green").save(buf, format="WEBP")
    return buf.getvalue()


def _mp4():
    def box(kind: bytes, payload: bytes = b"") -> bytes:
        return (len(payload) + 8).to_bytes(4, "big") + kind + payload

    return box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2mp41") + box(b"mdat")


class _RecordingStorage:
    def __init__(self):
        self.uploads: list[tuple[str, bytes, dict]] = []
        self.removed: list[list[str]] = []

    def from_(self, _bucket):
        return self

    def upload(self, key, content, options):
        self.uploads.append((key, content, options))

    def remove(self, keys):
        self.removed.append(list(keys))


def test_upload_draft_is_private_and_scoped_to_active_profile(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()

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
    assert len(db.storage.uploads) == 1


@pytest.mark.parametrize(("name", "content", "mime", "suffix"), [
    ("foto.jpg", _jpeg(), "image/jpeg", ".jpg"),
    ("foto.png", _png(), "image/png", ".png"),
    ("foto.gif", _gif(), "image/gif", ".gif"),
    ("foto.webp", _webp(), "image/webp", ".webp"),
])
def test_upload_draft_accepts_supported_real_media(fake_db, monkeypatch, name, content, mime, suffix):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()

    response = client.post("/posts/media-drafts", files={"file": (name, content, mime)})

    assert response.status_code == 201, response.text
    row = db.tables["temporary_media_uploads"][0]
    key, uploaded, options = db.storage.uploads[0]
    assert key.endswith(suffix)
    assert row["file_name"].endswith(suffix)
    assert row["size_bytes"] == len(uploaded)
    assert options["content-type"] == mime


def test_upload_draft_rebuilds_real_video_before_storage(fake_db, monkeypatch, tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg and shutil.which("ffprobe"), "ffmpeg e ffprobe sao necessarios para testar video"
    source = tmp_path / "source.mp4"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=32x32:d=0.5",
         "-metadata", "comment=PRIVATE_TEST_MARKER", "-c:v", "libx264", str(source)],
        check=True, timeout=15,
    )
    original = source.read_bytes()
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()

    response = client.post("/posts/media-drafts", files={"file": ("video.mp4", original, "video/mp4")})

    assert response.status_code == 201, response.text
    stored = db.storage.uploads[0][1]
    assert stored != original
    assert b"PRIVATE_TEST_MARKER" not in stored
    assert db.tables["temporary_media_uploads"][0]["size_bytes"] == len(stored)


def test_upload_draft_rejects_header_only_mp4(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()
    response = client.post("/posts/media-drafts", files={"file": ("video.mp4", _mp4(), "video/mp4")})
    assert response.status_code == 400
    assert db.storage.uploads == []


def test_upload_draft_rejects_wrong_extension(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()

    response = client.post(
        "/posts/media-drafts",
        files={"file": ("foto.png", _jpeg(), "image/png")},
    )

    assert response.status_code == 415
    assert response.json()["detail"].startswith("Arquivo inválido ou não suportado:")
    assert db.storage.uploads == []
    assert db.tables["temporary_media_uploads"] == []


def test_upload_draft_stores_sanitized_jpeg_without_appended_payload(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()
    malicious = _jpeg() + b"<script>alert(1)</script><?php echo 1; ?>SELECT * FROM users"

    response = client.post(
        "/posts/media-drafts",
        files={"file": ("oferta.jpg", malicious, "image/jpeg")},
    )

    assert response.status_code == 201, response.text
    uploaded = db.storage.uploads[0][1]
    assert b"<script" not in uploaded
    assert b"<?php" not in uploaded
    assert b"SELECT *" not in uploaded
    assert len(uploaded) < len(malicious)
    assert db.tables["temporary_media_uploads"][0]["size_bytes"] == len(uploaded)


def test_upload_draft_sanitizes_filename_traversal(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)

    response = client.post(
        "/posts/media-drafts",
        files={"file": ("../../evil\x01name.php.jpg", _jpeg(), "image/jpeg")},
    )

    assert response.status_code == 201, response.text
    row = db.tables["temporary_media_uploads"][0]
    assert row["file_name"] == "evilname.php.jpg"
    assert row["storage_key"].startswith("drafts/42/profile-a/")
    assert "evil" not in row["storage_key"]


@pytest.mark.parametrize(("name", "content", "mime"), [
    ("broken.jpg", _jpeg()[:12], "image/jpeg"),
    ("nota.txt", b"isso nao e midia", "text/plain"),
])
def test_upload_draft_rejects_invalid_media(fake_db, monkeypatch, name, content, mime):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()

    response = client.post("/posts/media-drafts", files={"file": (name, content, mime)})

    assert response.status_code in (400, 415)
    assert response.json()["detail"].startswith("Arquivo inválido ou não suportado:")
    assert db.storage.uploads == []
    assert db.tables["temporary_media_uploads"] == []


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
        "draft_media_ids": [DRAFT_1],
        "schedule": {"trigger": "date", "run_date": "2030-01-01T10:00:00"},
    }


def _batch_client(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.tables["temporary_media_uploads"].append({
        "id": DRAFT_1, "user_id": 42, "profile_id": "profile-a", "status": "ready",
        "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/offer.jpg",
        "file_name": "offer.jpg", "size_bytes": 12, "media_type": "IMAGE",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    })

    db.tables["x_credentials"] = [{
        "id": 1, "user_id": 42, "profile_id": "profile-a",
        "scope": "tweet.read tweet.write users.read media.write offline.access",
    }]

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


def test_preview_and_batch_block_disabled_x_without_blocking_threads(fake_db, monkeypatch):
    from api import network_limits

    monkeypatch.setitem(
        network_limits.DISABLED_NETWORKS,
        "x",
        "X estará disponível em um plano pago em breve",
    )
    client, db = _batch_client(fake_db, monkeypatch)

    preview = client.post("/posts/preview", json=_batch_body())
    assert preview.status_code == 200
    plans = {plan["network"]: plan for plan in preview.json()["plans"]}
    assert plans["threads"]["mode"] == "single_image"
    assert plans["x"]["mode"] == "blocked"
    assert plans["x"]["blocked_reason"] == "X estará disponível em um plano pago em breve"

    batch = client.post("/posts/batch", json=_batch_body())
    payload = batch.json()
    assert batch.status_code == 201
    assert [row["network"] for row in payload["created"]] == ["threads"]
    assert [(row["network"], row["blocked_reason"]) for row in payload["blocked"]] == [
        ("x", "X estará disponível em um plano pago em breve")
    ]
    assert [row["network"] for row in db.tables["posts"]] == ["threads"]


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
            "id": {"zzz": D_ZZZ, "aaa": D_AAA, "mmm": D_MMM}[name], "user_id": 42, "profile_id": "profile-a", "status": "ready",
            "storage_bucket": "post-media", "storage_key": f"drafts/{name}.jpg",
            "file_name": f"{name}.jpg", "size_bytes": 12, "media_type": "IMAGE",
            "expires_at": expires,
        })
    body = {
        "compositions": [{"network": "threads", "texts": ["copy"]}],
        "draft_media_ids": [D_ZZZ, D_AAA, D_MMM],
        "schedule": {"trigger": "date", "run_date": "2030-01-01T10:00:00"},
    }

    response = client.post("/posts/batch", json=body)

    assert response.status_code == 201
    names = {m["id"]: m["file_name"] for m in db.tables["medias"]}
    links = sorted(db.tables["posts_medias"], key=lambda r: r["display_order"])
    assert [r["display_order"] for r in links] == [0, 1, 2]
    assert [names[r["media_id"]] for r in links] == ["zzz.jpg", "aaa.jpg", "mmm.jpg"]


def test_batch_links_each_network_only_the_media_it_uses(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    for draft_id, name in ((D_ZZZ, "zzz.jpg"), (D_AAA, "aaa.jpg")):
        db.tables["temporary_media_uploads"].append({
            "id": draft_id, "user_id": 42, "profile_id": "profile-a", "status": "ready",
            "storage_bucket": "post-media", "storage_key": f"drafts/{name}",
            "file_name": name, "size_bytes": 12, "media_type": "IMAGE", "expires_at": expires,
        })
    body = {**_batch_body(), "draft_media_ids": [D_ZZZ, DRAFT_1, D_AAA]}

    preview = client.post("/posts/preview", json=body).json()["plans"]
    plans = {plan["network"]: plan for plan in preview}
    assert plans["threads"]["media_draft_ids"] == [D_ZZZ, DRAFT_1, D_AAA]
    assert plans["x"]["media_draft_ids"] == [D_ZZZ]
    assert [d["id"] for d in plans["x"]["dropped"]] == [DRAFT_1, D_AAA]

    response = client.post("/posts/batch", json=body)

    assert response.status_code == 201
    by_network = {row["network"]: row for row in response.json()["created"]}
    assert len(by_network["threads"]["medias"]) == 3
    assert [m["file_name"] for m in by_network["x"]["medias"]] == ["zzz.jpg"]
    x_links = [r for r in db.tables["posts_medias"] if r["post_id"] == by_network["x"]["post_id"]]
    assert len(x_links) == 1


class _BrokenLinksDB:
    """Delega ao FakeDB, mas o insert em posts_medias falha (strict, sem MagicMock)."""

    def __init__(self, inner):
        self._inner = inner
        self.storage = inner.storage

    @property
    def tables(self):
        return self._inner.tables

    def table(self, name):
        query = self._inner.table(name)
        if name == "posts_medias":
            def boom(_payload):
                raise RuntimeError("falha ao vincular")
            query.insert = boom
        return query


def test_batch_duplicate_draft_ids_link_media_once(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    body = {**_batch_body(), "draft_media_ids": [DRAFT_1, DRAFT_1]}

    response = client.post("/posts/batch", json=body)

    assert response.status_code == 201
    pairs = [(r["post_id"], r["media_id"]) for r in db.tables["posts_medias"]]
    assert len(pairs) == len(set(pairs)) == 2  # uma mídia por post (threads, x)


def test_batch_rejects_non_uuid_draft_id_with_422(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    body = {**_batch_body(), "draft_media_ids": ["nao-e-uuid"]}

    assert client.post("/posts/batch", json=body).status_code == 422
    assert client.post("/posts/preview", json=body).status_code == 422


def test_batch_link_failure_creates_no_job_and_undoes_everything(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    broken = _BrokenLinksDB(db)
    monkeypatch.setattr(posts_module, "supabase", broken)
    jobs = []

    async def fake_job(**kwargs):
        jobs.append(kwargs)
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)

    response = client.post("/posts/batch", json=_batch_body())

    assert response.status_code == 201
    payload = response.json()
    assert payload["created"] == []
    assert payload["group_id"] is None
    assert {p["network"] for p in payload["blocked"]} == {"threads", "x"}
    assert all(p["blocked_reason"] for p in payload["blocked"])
    assert jobs == []
    assert db.tables.get("posts", []) == []
    assert db.tables.get("medias", []) == []
    assert db.tables["temporary_media_uploads"][0]["status"] == "ready"


def test_batch_job_failure_keeps_media_for_next_network(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    calls = []

    async def flaky_job(**kwargs):
        calls.append(kwargs["post_id"])
        if len(calls) == 1:
            raise posts_module.InternalApiError("agendador fora")
        return "job-2"

    monkeypatch.setattr(posts_module, "create_scheduler_job", flaky_job)

    response = client.post("/posts/batch", json=_batch_body())

    payload = response.json()
    assert [c["network"] for c in payload["created"]] == ["x"]
    assert [b["network"] for b in payload["blocked"]] == ["threads"]
    assert len(db.tables["posts"]) == 1
    assert len(db.tables["medias"]) == 1
    assert [r["post_id"] for r in db.tables["posts_medias"]] == [payload["created"][0]["post_id"]]
    assert db.tables["temporary_media_uploads"][0]["status"] == "consumed"


class _RecordingDB:
    """Registra a ordem de update em rascunhos e insert em medias."""

    def __init__(self, inner, events):
        self._inner, self._events = inner, events
        self.storage = inner.storage

    @property
    def tables(self):
        return self._inner.tables

    def table(self, name):
        query = self._inner.table(name)
        if name == "temporary_media_uploads":
            real_update = query.update
            query.update = lambda payload: (self._events.append("claim"), real_update(payload))[1]
        if name == "medias":
            real_insert = query.insert
            query.insert = lambda payload: (self._events.append("media"), real_insert(payload))[1]
        return query


def test_batch_claims_draft_before_materializing_media(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    events = []
    monkeypatch.setattr(posts_module, "supabase", _RecordingDB(db, events))

    assert client.post("/posts/batch", json=_batch_body()).status_code == 201

    assert events[:2] == ["claim", "media"]
    assert events.count("media") == 1


def test_batch_blocks_network_when_draft_was_consumed_concurrently(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)
    stale = dict(db.tables["temporary_media_uploads"][0])
    db.tables["temporary_media_uploads"][0]["status"] = "consumed"  # outra requisição ganhou
    monkeypatch.setattr(posts_module, "_get_owned_ready_drafts", lambda *_a: [stale])

    payload = client.post("/posts/batch", json=_batch_body()).json()

    assert payload["created"] == []
    assert {b["network"] for b in payload["blocked"]} == {"threads", "x"}
    assert db.tables.get("medias", []) == []
    assert db.tables.get("posts", []) == []
    assert db.tables.get("posts_medias", []) == []


def test_batch_returns_draft_to_ready_when_every_network_fails(fake_db, monkeypatch):
    client, db = _batch_client(fake_db, monkeypatch)

    async def down(**_kwargs):
        raise posts_module.InternalApiError("agendador fora")

    monkeypatch.setattr(posts_module, "create_scheduler_job", down)

    payload = client.post("/posts/batch", json=_batch_body()).json()

    assert payload["created"] == []
    assert db.tables["temporary_media_uploads"][0]["status"] == "ready"
    assert db.tables.get("medias", []) == []


class _StrictStorage:
    def __init__(self, fail=False):
        self.removed: list[tuple[str, list[str]]] = []
        self._fail = fail
        self._bucket = None

    def from_(self, bucket):
        self._bucket = bucket
        return self

    def remove(self, keys):
        if self._fail:
            raise RuntimeError("storage fora")
        self.removed.append((self._bucket, list(keys)))


def _storage_db(fake_db, monkeypatch, tables=None, fail=False):
    db = fake_db(tables or {})
    db.storage = _StrictStorage(fail=fail)
    monkeypatch.setattr(posts_module, "supabase", db)
    return db


STORAGE_PATH = "storage://post-media/drafts/42/profile-a/offer.jpg"


def test_remove_media_file_deletes_durable_object_and_consumed_draft_row(fake_db, monkeypatch):
    db = _storage_db(fake_db, monkeypatch, {"temporary_media_uploads": [
        {"id": "a", "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/offer.jpg", "status": "consumed"},
        {"id": "b", "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/other.jpg", "status": "consumed"},
    ]})

    posts_module._remove_media_file(STORAGE_PATH)

    assert db.storage.removed == [("post-media", ["drafts/42/profile-a/offer.jpg"])]
    assert [r["id"] for r in db.tables["temporary_media_uploads"]] == ["b"]


@pytest.mark.parametrize("path", [
    "storage://outro-bucket/drafts/42/profile-a/offer.jpg",
    "storage://post-media/../outro/x.jpg",
    "storage://post-media/drafts/../../x.jpg",
    "storage://post-media/",
    "storage://post-media",
    "storage:///drafts/x.jpg",
    "storage://post-media//x.jpg",
])
def test_remove_media_file_never_trusts_storage_path_outside_expected_bucket(fake_db, monkeypatch, path):
    db = _storage_db(fake_db, monkeypatch)

    posts_module._remove_media_file(path)

    assert db.storage.removed == []


def test_remove_media_file_storage_failure_only_logs_and_keeps_draft_row(fake_db, monkeypatch):
    db = _storage_db(fake_db, monkeypatch, {"temporary_media_uploads": [
        {"id": "a", "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/offer.jpg", "status": "consumed"},
    ]}, fail=True)

    posts_module._remove_media_file(STORAGE_PATH)  # não levanta

    assert len(db.tables["temporary_media_uploads"]) == 1


def test_delete_thread_cascade_removes_durable_media_of_consumed_draft(fake_db, monkeypatch):
    db = _storage_db(fake_db, monkeypatch, {
        "posts_medias": [{"post_id": 7, "media_id": 5, "medias": {"id": 5, "file_path": STORAGE_PATH}}],
        "medias": [{"id": 5, "file_path": STORAGE_PATH}],
        "posts": [{"id": 7}],
        "temporary_media_uploads": [
            {"id": "a", "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/offer.jpg", "status": "consumed"},
        ],
    })
    monkeypatch.setattr(posts_module, "_get_thread_chain", lambda head_id: [{"id": head_id}])

    posts_module._delete_thread_cascade(7)

    assert db.storage.removed == [("post-media", ["drafts/42/profile-a/offer.jpg"])]
    assert db.tables["medias"] == []
    assert db.tables["temporary_media_uploads"] == []


def test_delete_thread_cascade_keeps_durable_media_shared_with_another_post(fake_db, monkeypatch):
    db = _storage_db(fake_db, monkeypatch, {
        "posts_medias": [
            {"post_id": 7, "media_id": 5, "medias": {"id": 5, "file_path": STORAGE_PATH}},
            {"post_id": 8, "media_id": 5},
        ],
        "medias": [{"id": 5, "file_path": STORAGE_PATH}],
        "posts": [{"id": 7}],
    })
    monkeypatch.setattr(posts_module, "_get_thread_chain", lambda head_id: [{"id": head_id}])

    posts_module._delete_thread_cascade(7)

    assert db.storage.removed == []
    assert len(db.tables["medias"]) == 1


class _CallLogDB:
    """Registra toda chamada table(nome).op(), em ordem."""

    def __init__(self, inner, log):
        self._inner, self._log = inner, log
        self.storage = inner.storage

    @property
    def tables(self):
        return self._inner.tables

    def table(self, name):
        query = self._inner.table(name)
        for op in ("insert", "update", "delete"):
            real = getattr(query, op)
            setattr(query, op, lambda *a, _r=real, _n=name, _o=op: (self._log.append((_n, _o)), _r(*a))[1])
        return query


def test_batch_links_media_right_after_creating_it(fake_db, monkeypatch):
    """Janela do gatilho da 014: nada entre insert em medias e em posts_medias."""
    client, db = _batch_client(fake_db, monkeypatch)
    log = []
    monkeypatch.setattr(posts_module, "supabase", _CallLogDB(db, log))

    assert client.post("/posts/batch", json=_batch_body()).status_code == 201

    at = log.index(("medias", "insert"))
    assert log[at + 1] == ("posts_medias", "insert")


def test_shopee_photo_url_allowlist_rejects_ssrf_hosts():
    from fastapi import HTTPException
    valid = "https://cf.shopee.com.br/file/valid"
    assert posts_module._check_shopee_image_url(valid) == valid
    for attack in (
        "http://cf.shopee.com.br/file/1",
        "https://cf.shopee.com.br.evil.example/file/1",
        "https://127.0.0.1/internal",
        "https://cf.shopee.com.br@127.0.0.1/private",
        "https://cf.shopee.com.br:8080/file/1",
        "https://[not-an-ipv6]/file/1",
        "file:///etc/passwd",
    ):
        with pytest.raises(HTTPException) as err:
            posts_module._check_shopee_image_url(attack)
        assert err.value.status_code == 400


def test_import_shopee_product_photo_persists_private_draft(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()
    db.tables["products"] = [{
        "id": 7, "user_id": 42, "profile_id": "profile-a",
        "image": "https://cf.shopee.com.br/file/example",
    }]

    async def trusted_download(url):
        assert url == "https://cf.shopee.com.br/file/example"
        return bytearray(_jpeg() + b"<script>bad</script>")

    monkeypatch.setattr(posts_module, "_download_shopee_image", trusted_download)
    response = client.post("/posts/product-image-drafts/7")
    assert response.status_code == 201, response.text
    draft = response.json()
    assert draft["status"] == "ready"
    assert draft["profile_id"] == "profile-a"
    assert "storage_key" not in draft
    assert "image" not in draft
    assert len(db.storage.uploads) == 1
    stored = db.storage.uploads[0][1]
    assert b"<script>" not in stored
    assert db.tables["temporary_media_uploads"][0]["media_type"] == "IMAGE"
    assert db.tables["temporary_media_uploads"][0]["user_id"] == 42


def test_import_shopee_product_photo_rejects_foreign_profile(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch, profile_id="profile-b")
    db.storage = _RecordingStorage()
    db.tables["products"] = [{
        "id": 7, "user_id": 42, "profile_id": "profile-a",
        "image": "https://cf.shopee.com.br/file/example",
    }]

    async def forbidden_download(_url):
        raise AssertionError("Nunca baixar imagem de outro perfil")

    monkeypatch.setattr(posts_module, "_download_shopee_image", forbidden_download)
    response = client.post("/posts/product-image-drafts/7")
    assert response.status_code == 404
    assert db.storage.uploads == []
    assert db.tables["temporary_media_uploads"] == []


def test_import_shopee_product_photo_rejects_missing_and_invalid_media(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()
    db.tables["products"] = [{"id": 9, "user_id": 42, "profile_id": "profile-a", "image": None}]
    assert client.post("/posts/product-image-drafts/9").status_code == 400

    db.tables["products"][0]["image"] = "https://cf.shopee.com.br/file/example"

    async def fake_download(_url):
        return bytearray(b"<html>not an image</html>")

    monkeypatch.setattr(posts_module, "_download_shopee_image", fake_download)
    assert client.post("/posts/product-image-drafts/9").status_code == 415
    assert db.storage.uploads == []
    assert db.tables["temporary_media_uploads"] == []


def test_import_shopee_png_is_normalized_to_jpeg(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.storage = _RecordingStorage()
    db.tables["products"] = [{
        "id": 11, "user_id": 42, "profile_id": "profile-a",
        "image": "https://cf.shopee.com.br/file/example",
    }]

    async def png_download(_url):
        return bytearray(_png())

    monkeypatch.setattr(posts_module, "_download_shopee_image", png_download)
    response = client.post("/posts/product-image-drafts/11")
    assert response.status_code == 201, response.text
    key, payload, options = db.storage.uploads[0]
    assert key.endswith(".jpg")
    assert payload.startswith(b"\xff\xd8\xff")
    assert options["content-type"] == "image/jpeg"

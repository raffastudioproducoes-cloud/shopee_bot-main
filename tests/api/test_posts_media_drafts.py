"""Rascunhos duraveis de mídia: propriedade por perfil e limpeza segura."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from fastapi.testclient import TestClient

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

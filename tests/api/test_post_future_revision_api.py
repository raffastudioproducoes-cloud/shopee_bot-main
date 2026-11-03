"""F1/R12: endpoint de edição futura, sem side effects reais."""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


def _client(monkeypatch, *, scheduled=True, immediate=False):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    monkeypatch.setattr(posts, "_get_post", lambda *_: {
        "id": 10, "user_id": 42, "profile_id": "profile-a",
        "post_id": None, "publish_immediately": immediate, "network": "threads",
    })
    monkeypatch.setattr(posts, "_get_post_schedule_entries",
                        lambda *_: [{"trigger": "cron", "id": "agenda"}] if scheduled else [])
    monkeypatch.setattr(posts, "_get_post_products", lambda *_: [{"id": 99}])
    monkeypatch.setattr(posts, "_revision_media_snapshot", lambda *_: [
        {"id": 22, "file_path": "storage://post-media/post.jpg", "size": 100,
         "file_name": "post.jpg", "type": "IMAGE"},
    ])
    monkeypatch.setattr(posts, "_check_network_rules", lambda *_a, **_k: None)
    database = MagicMock()
    database.rpc.return_value.execute.return_value.data = [
        {"revision_id": 7, "cutover_at": "2026-11-02T15:30:00+00:00"}
    ]
    monkeypatch.setattr(posts, "supabase", database)
    return TestClient(app), database


def test_auth_required_for_future_edit():
    app.dependency_overrides.clear()
    try:
        response = TestClient(app).post("/posts/10/future-revisions", json={
            "texts": ["novo"], "product_ids": [99],
        })
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_future_edit_creates_new_snapshot_without_updating_legacy_posts(monkeypatch):
    client, database = _client(monkeypatch)
    try:
        result = client.post("/posts/10/future-revisions", json={
            "texts": ["texto novo"], "product_ids": [99],
        })
        assert result.status_code == 201
        assert result.json()["revision_id"] == 7
        database.rpc.assert_called_once()
        name, parameters = database.rpc.call_args.args
        assert name == "create_future_post_revision"
        assert parameters["p_post_id"] == 10
        assert parameters["p_user_id"] == "42"
        assert parameters["p_profile_id"] == "profile-a"
        assert parameters["p_snapshot"]["texts"] == ["texto novo"]
        assert parameters["p_snapshot"]["medias"][0]["id"] == 22
        database.table.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_no_schedule_means_no_revision_or_mutation(monkeypatch):
    client, database = _client(monkeypatch, scheduled=False)
    try:
        response = client.post("/posts/10/future-revisions", json={
            "texts": ["x"], "product_ids": [99],
        })
        assert response.status_code == 409
        database.rpc.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_immediate_post_is_never_revised(monkeypatch):
    client, database = _client(monkeypatch, immediate=True)
    try:
        response = client.post("/posts/10/future-revisions", json={
            "texts": ["x"], "product_ids": [99],
        })
        assert response.status_code == 409
        database.rpc.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_product_swap_is_rejected_without_damaging_original(monkeypatch):
    client, database = _client(monkeypatch)
    try:
        response = client.post("/posts/10/future-revisions", json={
            "texts": ["x"], "product_ids": [123],
        })
        assert response.status_code == 422
        database.rpc.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_db_cutover_rejection_is_propagated_as_conflict(monkeypatch):
    client, database = _client(monkeypatch)
    database.rpc.return_value.execute.side_effect = RuntimeError("NO_EDITABLE_FUTURE_SLOTS")
    try:
        response = client.post("/posts/10/future-revisions", json={
            "texts": ["x"], "product_ids": [99],
        })
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()

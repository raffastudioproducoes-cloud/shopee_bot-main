"""Contratos: agenda detalhada e imutabilidade do conteúdo de posts em execução.

Todos os testes usam o fake Supabase em memória. Nenhuma publicação é disparada.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


@pytest.fixture
def post_client(fake_db, monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"

    db = fake_db({
        "posts": [{
            "id": 101,
            "user_id": 42,
            "profile_id": "profile-a",
            "post_id": None,
            "network": "threads",
            "text": "texto original",
            "created_at": "2026-11-01T10:00:00Z",
            "publish_immediately": False,
        }],
        "schedulers": [],
        "publish_jobs": [],
        "activities": [],
        "posts_products": [],
        "posts_medias": [],
    })
    monkeypatch.setattr(posts_module, "supabase", db)
    yield TestClient(app), db
    app.dependency_overrides.clear()


def _recurring_rows():
    rows = []
    for number, hour in enumerate(("09:30:00", "13:30:00", "18:30:00"), start=1):
        rows.append({
            "id": f"cron-{number}",
            "post_id": 101,
            "user_id": 42,
            "trigger": "cron",
            "run_date": None,
            "time": hour,
            "day_of_week": 0,
            "days_of_week": [0, 2, 4],
            "start_date": "2026-11-02T00:00:00",
        })
    rows.append({
        "id": "outro-usuario",
        "post_id": 101,
        "user_id": 99,
        "trigger": "cron",
        "time": "23:00:00",
        "days_of_week": [6],
    })
    return rows


def test_get_and_list_include_all_recurring_times_but_not_another_users(post_client):
    client, db = post_client
    db.tables["schedulers"] = _recurring_rows()

    listing = client.get("/posts")
    assert listing.status_code == 200
    items = listing.json()["data"]
    assert len(items) == 1
    post = items[0]

    detail_res = client.get("/posts/101")
    assert detail_res.status_code == 200
    detail = detail_res.json()

    for item in (post, detail):
        assert item["schedule_trigger"] == "cron"
        assert item["scheduled"] is True
        entries = item["schedule_entries"]
        assert len(entries) == 3
        assert [e["time"] for e in entries] == ["09:30:00", "13:30:00", "18:30:00"]
        assert all(e["days_of_week"] == [0, 2, 4] for e in entries)
        assert all(e["id"] != "outro-usuario" for e in entries)


@pytest.mark.parametrize("method,url,kwargs", [
    ("put", "/posts/101", {"json": {"texts": ["hack"], "product_ids": []}}),
    ("post", "/posts/101/media", {"files": {"file": ("foto.jpg", b"falso", "image/jpeg")}}),
    ("delete", "/posts/101/media/77", {}),
])
def test_recurring_post_rejects_editing_and_media_mutations(post_client, method, url, kwargs):
    client, db = post_client
    db.tables["schedulers"] = _recurring_rows()

    response = getattr(client, method)(url, **kwargs)
    assert response.status_code == 409
    assert db.tables["posts"][0]["text"] == "texto original"
    assert db.tables["posts_medias"] == []


@pytest.mark.parametrize("blocked_by", ["immediate", "publish_job", "activity"])
def test_post_with_publication_history_rejects_content_edits(post_client, blocked_by):
    client, db = post_client
    if blocked_by == "immediate":
        db.tables["posts"][0]["publish_immediately"] = True
    elif blocked_by == "publish_job":
        db.tables["publish_jobs"].append({
            "id": "job-1", "user_id": 42, "profile_id": "profile-a",
            "post_id": 101, "status": "succeeded", "created_at": "2026-11-01T11:00:00Z",
        })
    else:
        db.tables["activities"].append({
            "activity_id": 1, "user_id": 42, "profile_id": "profile-a",
            "metadata->>post_id": "101",
        })
    response = client.put("/posts/101", json={"texts": ["hack"], "product_ids": []})
    assert response.status_code == 409
    assert db.tables["posts"][0]["text"] == "texto original"


def test_post_from_different_profile_returns_404_not_409(post_client):
    client, db = post_client
    db.tables["schedulers"] = _recurring_rows()
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-b"
    assert client.get("/posts/101").status_code == 404
    assert client.put("/posts/101", json={"texts": ["hack"], "product_ids": []}).status_code == 404
    assert client.delete("/posts/101/media/77").status_code == 404


def test_unscheduled_draft_still_allows_explicit_api_update(post_client):
    client, db = post_client
    response = client.put("/posts/101", json={"texts": ["texto revisado"], "product_ids": []})
    assert response.status_code == 200
    assert db.tables["posts"][0]["text"] == "texto revisado"

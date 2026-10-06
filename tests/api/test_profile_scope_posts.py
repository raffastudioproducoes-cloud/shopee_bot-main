"""Multi-perfil: posts/mídias isolados por perfil ativo; sem perfil, por user_id."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def make_client(fake_db, monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    db = fake_db({
        "posts": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "text": "do A", "post_id": None,
             "created_at": "2026-01-01"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "text": "do B", "post_id": None,
             "created_at": "2026-01-02"},
        ],
        "medias": [{"id": 5, "user_id": 42, "profile_id": "profile-b", "file_path": "x.jpg"}],
    })
    monkeypatch.setattr(posts_module, "supabase", db)

    def _make(cookie=None):
        c = TestClient(app)
        if cookie:
            c.cookies.update(cookie)
        return c

    yield db, _make
    app.dependency_overrides.clear()


def test_list_posts_only_active_profile(make_client, profile_cookie):
    _db, make = make_client
    ids = [p["id"] for p in make(profile_cookie("profile-a")).get("/posts").json()["data"]]
    assert ids == [1]


def test_list_posts_without_profile_falls_back_to_user_scope(make_client, old_token_without_profile_claim):
    _db, make = make_client
    ids = {p["id"] for p in make(old_token_without_profile_claim).get("/posts").json()["data"]}
    assert ids == {1, 2}


def test_get_post_from_other_profile_is_404(make_client, profile_cookie):
    _db, make = make_client
    assert make(profile_cookie("profile-a")).get("/posts/2").status_code == 404


def test_update_post_from_other_profile_is_404_and_untouched(make_client, profile_cookie):
    db, make = make_client
    res = make(profile_cookie("profile-a")).put("/posts/2", json={"texts": ["hack"]})
    assert res.status_code == 404
    assert db.tables["posts"][1]["text"] == "do B"


def test_delete_post_from_other_profile_is_404_and_kept(make_client, profile_cookie):
    db, make = make_client
    assert make(profile_cookie("profile-a")).delete("/posts/2").status_code == 404
    assert {p["id"] for p in db.tables["posts"]} == {1, 2}


def test_delete_media_from_other_profile_post_is_404(make_client, profile_cookie):
    db, make = make_client
    assert make(profile_cookie("profile-a")).delete("/posts/2/media/5").status_code == 404
    assert len(db.tables["medias"]) == 1


def test_create_post_stores_profile_id_and_forwards_it_to_scheduler(make_client, profile_cookie, monkeypatch):
    db, make = make_client
    sent = {}

    async def fake_create_job(**kwargs):
        sent.update(kwargs)
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_create_job)

    res = make(profile_cookie("profile-a")).post("/posts", json={
        "texts": ["parte 1", "parte 2"],
        "schedule": {"trigger": "date", "run_date": "2026-12-01T10:00:00"},
    })

    assert res.status_code == 201
    created = [p for p in db.tables["posts"] if p["id"] > 1000]
    assert len(created) == 2 and all(p["profile_id"] == "profile-a" for p in created)
    assert sent["profile_id"] == "profile-a"


def test_create_post_without_profile_omits_profile_id(make_client, old_token_without_profile_claim, monkeypatch):
    db, make = make_client
    sent = {}

    async def fake_create_job(**kwargs):
        sent.update(kwargs)
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_create_job)
    make(old_token_without_profile_claim).post("/posts", json={
        "texts": ["x"], "schedule": {"trigger": "date", "run_date": "2026-12-01T10:00:00"},
    })
    created = [p for p in db.tables["posts"] if p["id"] > 1000]
    assert "profile_id" not in created[0]
    assert "profile_id" not in sent

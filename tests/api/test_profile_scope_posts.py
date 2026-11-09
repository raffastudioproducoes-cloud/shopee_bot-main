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
        "schedule": {"trigger": "cron", "time": "10:00", "days_of_week": [0]},
    })

    assert res.status_code == 201
    created = [p for p in db.tables["posts"] if p["id"] > 1000]
    assert len(created) == 2 and all(p["profile_id"] == "profile-a" for p in created)
    assert sent["profile_id"] == "profile-a"


def test_create_post_without_profile_is_rejected_before_creating_a_job(make_client, old_token_without_profile_claim, monkeypatch):
    db, make = make_client
    sent = {}

    async def fake_create_job(**kwargs):
        sent.update(kwargs)
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_create_job)
    res = make(old_token_without_profile_claim).post("/posts", json={
        "texts": ["x"], "schedule": {"trigger": "cron", "time": "10:00", "days_of_week": [0]},
    })
    assert res.status_code == 400
    assert [p for p in db.tables["posts"] if p["id"] > 1000] == []
    assert sent == {}


@pytest.fixture
def product_db(fake_db, monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    db = fake_db({
        "posts": [{"id": 1, "user_id": 42, "profile_id": "profile-a", "text": "do A", "post_id": None}],
        "products": [
            {"id": 10, "user_id": 42, "profile_id": "profile-a"},
            {"id": 11, "user_id": 99, "profile_id": "profile-x"},
            {"id": 12, "user_id": 42, "profile_id": "profile-b"},
        ],
    })
    monkeypatch.setattr(posts_module, "supabase", db)
    yield db
    app.dependency_overrides.clear()


def test_update_post_rejects_products_not_owned_and_keeps_post(product_db, profile_cookie):
    c = TestClient(app)
    c.cookies.update(profile_cookie("profile-a"))
    res = c.put("/posts/1", json={"texts": ["novo"], "product_ids": [11]})
    assert res.status_code == 400
    assert product_db.tables["posts"][0]["text"] == "do A"
    assert product_db.tables.get("posts_products", []) == []


def test_update_post_accepts_product_from_another_profile_of_same_account(product_db, profile_cookie):
    c = TestClient(app)
    c.cookies.update(profile_cookie("profile-a"))

    res = c.put("/posts/1", json={"texts": ["novo"], "product_ids": [12]})

    assert res.status_code == 200
    assert [r["product_id"] for r in product_db.tables["posts_products"]] == [12]


def test_update_post_accepts_own_products(product_db, profile_cookie):
    c = TestClient(app)
    c.cookies.update(profile_cookie("profile-a"))
    res = c.put("/posts/1", json={"texts": ["novo"], "product_ids": [10]})
    assert res.status_code == 200
    assert [r["product_id"] for r in product_db.tables["posts_products"]] == [10]


def test_create_post_rejects_foreign_product_without_creating(product_db, profile_cookie):
    c = TestClient(app)
    c.cookies.update(profile_cookie("profile-a"))
    res = c.post("/posts", json={
        "texts": ["x"], "network": "threads", "product_ids": [11],
        "schedule": {"trigger": "cron", "time": "10:00", "days_of_week": [0]},
    })
    assert res.status_code == 400, res.text
    assert len(product_db.tables["posts"]) == 1


def test_legacy_token_without_claim_falls_back_to_principal_profile(real_profile_resolution, fake_db, monkeypatch, old_token_without_profile_claim):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    db = fake_db({
        "profiles": [
            {"id": "profile-a", "user_id": 42, "kind": "principal"},
            {"id": "profile-b", "user_id": 42, "kind": "secundario"},
        ],
        "posts": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "text": "A", "post_id": None, "created_at": "2026-01-01"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "text": "B", "post_id": None, "created_at": "2026-01-02"},
        ],
    })
    monkeypatch.setattr(posts_module, "supabase", db)
    from api.routers import profiles as profiles_module
    monkeypatch.setattr(profiles_module, "supabase", db)
    c = TestClient(app)
    c.cookies.update(old_token_without_profile_claim)
    assert [p["id"] for p in c.get("/posts").json()["data"]] == [1]
    app.dependency_overrides.clear()


def test_delete_campaign_post_is_allowed_and_cancels_its_slot(make_client, profile_cookie):
    db, make = make_client
    db.tables["posts"].append({"id": 3, "user_id": 42, "profile_id": "profile-a", "text": "camp", "post_id": None,
                               "created_at": "2026-01-03", "publication_origin": "campaign"})
    db.tables["schedulers"] = []
    db.tables["posts_medias"] = []
    db.tables["posts_products"] = []
    db.tables["campaign_network_slots_f4e"] = [{"id": "s1", "post_id": 3, "state": "planned"}]
    res = make(profile_cookie("profile-a")).delete("/posts/3")
    assert res.status_code == 200
    assert 3 not in {p["id"] for p in db.tables["posts"]}
    slot = db.tables["campaign_network_slots_f4e"][0]
    assert slot["state"] == "cancelled" and slot["finished_at"]


def test_delete_campaign_post_being_published_is_refused(make_client, profile_cookie):
    db, make = make_client
    db.tables["posts"].append({"id": 3, "user_id": 42, "profile_id": "profile-a", "text": "camp", "post_id": None,
                               "created_at": "2026-01-03", "publication_origin": "campaign"})
    db.tables["campaign_network_slots_f4e"] = [{"id": "s1", "post_id": 3, "state": "running"}]
    res = make(profile_cookie("profile-a")).delete("/posts/3")
    assert res.status_code == 409
    assert 3 in {p["id"] for p in db.tables["posts"]}

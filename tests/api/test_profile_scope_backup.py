"""Multi-perfil: backup/restore escopados ao perfil ativo, HMAC e backups antigos preservados."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import lists as lists_module
from api.routers import posts as posts_module
from api.routers import users as users_module
from api.routers.auth import get_current_user_id


@pytest.fixture
def env(fake_db, monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    db = fake_db({
        "products": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "product_id": "111", "name": "Do A"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "product_id": "222", "name": "Do B"},
        ],
        "product_lists": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "name": "Lista A"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "name": "Lista B"},
        ],
        "posts": [
            {"id": 1, "user_id": 42, "profile_id": "profile-a", "text": "post A", "post_id": None, "network": "threads"},
            {"id": 2, "user_id": 42, "profile_id": "profile-b", "text": "post B", "post_id": None, "network": "threads"},
        ],
    })
    for module in (users_module, lists_module, posts_module):
        monkeypatch.setattr(module, "supabase", db)

    def _client(cookie=None):
        c = TestClient(app)
        if cookie:
            c.cookies.update(cookie)
        return c

    yield db, _client
    app.dependency_overrides.clear()


def test_export_contains_only_active_profile_data(env, profile_cookie):
    _db, client = env
    body = client(profile_cookie("profile-a")).get("/users/me/backup").json()
    assert [p["name"] for p in body["products"]] == ["Do A"]
    assert [p["name"] for p in body["product_lists"]] == ["Lista A"]
    assert [p["texts"] for p in body["posts"]] == [["post A"]]


def test_export_without_profile_falls_back_to_whole_account(env, old_token_without_profile_claim):
    _db, client = env
    body = client(old_token_without_profile_claim).get("/users/me/backup").json()
    assert len(body["products"]) == 2 and len(body["posts"]) == 2


def test_restore_of_exported_backup_keeps_valid_hmac_and_writes_active_profile(env, profile_cookie):
    db, client = env
    backup = client(profile_cookie("profile-a")).get("/users/me/backup").json()
    # restaura o backup do perfil A dentro do perfil C (HMAC do export segue válido)
    res = client(profile_cookie("profile-c")).post("/users/me/restore", json=backup)
    assert res.status_code == 200
    new_lists = [p for p in db.tables["product_lists"] if p["id"] > 1000]
    new_posts = [p for p in db.tables["posts"] if p["id"] > 1000]
    assert [p["profile_id"] for p in new_lists] == ["profile-c"]
    assert [p["profile_id"] for p in new_posts] == ["profile-c"]
    # 041: o mesmo produto pode existir em 2 perfis -- A mantém o seu, C ganha uma cópia
    assert sorted(p["profile_id"] for p in db.tables["products"] if p["product_id"] == "111") == ["profile-a", "profile-c"]


def test_restore_into_same_profile_writes_profile_id_on_products(env, profile_cookie):
    db, client = env
    backup = client(profile_cookie("profile-a")).get("/users/me/backup").json()
    assert client(profile_cookie("profile-a")).post("/users/me/restore", json=backup).status_code == 200
    # produto 111 já é do perfil A: atualizado no lugar, sem duplicar
    assert [p["profile_id"] for p in db.tables["products"] if p["product_id"] == "111"] == ["profile-a"]


def test_restore_old_backup_without_profile_fields_is_accepted(env, profile_cookie):
    db, client = env
    payload = {
        "products": [{"id": 9, "product_id": "999", "name": "Antigo", "profile_id": "profile-a"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum({k: v for k, v in payload.items()})
    assert client(profile_cookie("profile-b")).post("/users/me/restore", json=payload).status_code == 200
    created = [p for p in db.tables["products"] if p["id"] > 1000]
    assert created[0]["profile_id"] == "profile-b"  # profile_id vindo do arquivo é ignorado


def test_restore_creates_copy_for_active_profile_without_touching_other_profile(env, profile_cookie):
    db, client = env
    payload = {
        "products": [{"id": 1, "product_id": "111", "name": "Copia em B"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum(dict(payload))
    assert client(profile_cookie("profile-b")).post("/users/me/restore", json=payload).status_code == 200
    rows = {p["profile_id"]: p["name"] for p in db.tables["products"] if p["product_id"] == "111"}
    assert rows == {"profile-a": "Do A", "profile-b": "Copia em B"}


def test_restore_updates_existing_product_of_same_profile_instead_of_duplicating(env, profile_cookie):
    db, client = env
    payload = {
        "products": [{"id": 1, "product_id": "111", "name": "Renomeado"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum(dict(payload))
    assert client(profile_cookie("profile-a")).post("/users/me/restore", json=payload).status_code == 200
    assert [p["name"] for p in db.tables["products"] if p["product_id"] == "111"] == ["Renomeado"]
    assert len(db.tables["products"]) == 2


def test_restore_without_profile_does_not_set_profile_id(env, old_token_without_profile_claim):
    db, client = env
    payload = {
        "products": [{"id": 9, "product_id": "999", "name": "Sem perfil"}],
        "product_lists": [], "posts": [], "exported_at": "2026-01-01T00:00:00+00:00",
    }
    payload["checksum"] = users_module._checksum(dict(payload))
    assert client(old_token_without_profile_claim).post("/users/me/restore", json=payload).status_code == 200
    created = [p for p in db.tables["products"] if p["id"] > 1000]
    assert "profile_id" not in created[0]


def test_post_product_same_id_in_two_profiles_coexists_and_duplicate_in_same_profile_is_409(env, profile_cookie, monkeypatch):
    from api.routers import products as products_module

    db, client = env
    monkeypatch.setattr(products_module, "supabase", db)  # env só troca users/lists/posts
    body = {"product_id": "777", "name": "Mesmo produto"}
    assert client(profile_cookie("profile-a")).post("/products", json=body).status_code == 201
    assert client(profile_cookie("profile-b")).post("/products", json=body).status_code == 201
    assert sorted(p["profile_id"] for p in db.tables["products"] if p["product_id"] == "777") == ["profile-a", "profile-b"]
    dup = client(profile_cookie("profile-a")).post("/products", json=body)
    assert dup.status_code == 409
    assert len([p for p in db.tables["products"] if p["product_id"] == "777"]) == 2

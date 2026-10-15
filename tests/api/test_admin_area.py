"""As rotas administrativas novas reutilizam os handlers e exigem ADMIN."""
import pytest
from fastapi.testclient import TestClient

from api import database
from api.main import app
from api.routers.auth import get_current_user_id


ROUTES = [
    ("GET", "/admin/users"), ("POST", "/admin/users"),
    ("GET", "/admin/users/other"), ("PUT", "/admin/users/other"),
    ("DELETE", "/admin/users/other"), ("GET", "/admin/logs"), ("GET", "/admin/credentials/status"),
]


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize("method,path", ROUTES)
def test_admin_routes_require_authentication(method, path):
    assert TestClient(app).request(method, path).status_code == 401


@pytest.mark.parametrize("method,path", ROUTES)
def test_admin_routes_reject_common_user(method, path, monkeypatch, fake_db):
    db = fake_db({"users": [{"id": "owner", "access": "USER"}]})
    monkeypatch.setattr(database, "get_supabase", lambda: db)
    app.dependency_overrides[get_current_user_id] = lambda: "owner"
    assert TestClient(app).request(method, path).status_code == 403


def test_admin_lists_accounts_with_existing_pagination(monkeypatch, fake_db):
    db = fake_db({"users": [{"id": "owner", "access": "ADMIN", "username": "admin", "created_at": "2026-10-15"}]})
    monkeypatch.setattr(database, "get_supabase", lambda: db)
    app.dependency_overrides[get_current_user_id] = lambda: "owner"
    response = TestClient(app).get("/admin/users", params={"limit": 1})
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "owner"
    assert response.json()["next_cursor"] == "2026-10-15"


@pytest.mark.parametrize("method,path", [
    ("GET", "/users"), ("POST", "/users"), ("GET", "/users/other"),
    ("PUT", "/users/other"), ("DELETE", "/users/other"), ("GET", "/logs"),
])
def test_legacy_admin_routes_are_gone(method, path):
    assert TestClient(app).request(method, path).status_code in (404, 405)


def test_pending_migration_051_is_not_in_auto_applied_folder():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert not list((root / "database" / "migrations").glob("051*"))
    assert (root / "docs" / "migrations-pendentes" / "051_admin_metrics_snapshot.sql").exists()

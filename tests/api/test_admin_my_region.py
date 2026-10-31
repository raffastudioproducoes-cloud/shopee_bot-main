"""Private own-region marker must not bypass aggregation threshold for customers."""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api import database
from api.main import app
from api.routers import admin
from api.routers.auth import get_current_user_id


def _auth(monkeypatch, role="ADMIN"):
    app.dependency_overrides.clear()
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"access": role}
    )
    monkeypatch.setattr(database, "get_supabase", lambda: db)
    app.dependency_overrides[get_current_user_id] = lambda: "owner-uuid"
    return db


def test_my_region_requires_authentication():
    app.dependency_overrides.clear()
    assert TestClient(app).get("/admin/my-region").status_code == 401


def test_my_region_denies_non_admin(monkeypatch):
    _auth(monkeypatch, role="USER")
    region_db = MagicMock()
    monkeypatch.setattr(admin, "supabase", region_db)
    try:
        assert TestClient(app).get("/admin/my-region").status_code == 403
        region_db.table.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_my_region_returns_only_authenticated_owners_region(monkeypatch):
    _auth(monkeypatch)
    region_db = MagicMock()
    region_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"region": "BR-RJ", "user_id": "private-user-id", "latitude": -22.9}
    )
    monkeypatch.setattr(admin, "supabase", region_db)
    try:
        response = TestClient(app).get("/admin/my-region")
        assert response.status_code == 200
        assert response.json() == {"region": "BR-RJ"}
        region_db.table.assert_called_once_with("account_region_preferences")
        region_db.table.return_value.select.assert_called_once_with("region")
        region_db.table.return_value.select.return_value.eq.assert_called_once_with("user_id", "owner-uuid")
        assert "private-user-id" not in response.text
        assert "latitude" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_my_region_empty_without_opt_in(monkeypatch):
    _auth(monkeypatch)
    region_db = MagicMock()
    region_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    monkeypatch.setattr(admin, "supabase", region_db)
    try:
        response = TestClient(app).get("/admin/my-region")
        assert response.status_code == 200
        assert response.json() == {"region": None}
    finally:
        app.dependency_overrides.clear()

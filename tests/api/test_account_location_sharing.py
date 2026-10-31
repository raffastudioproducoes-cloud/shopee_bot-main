"""Regressões: a coleta de localização é única, voluntária e revogável."""
import pytest
from fastapi.testclient import TestClient

from api import database
from api.main import app
from api.routers.auth import get_current_user_id


@pytest.fixture
def context(monkeypatch, fake_db):
    account_id = "11111111-1111-4111-8111-111111111111"
    admin_id = "22222222-2222-4222-8222-222222222222"
    db = fake_db({
        "users": [
            {"id": account_id, "access": "USER"},
            {"id": admin_id, "access": "ADMIN"},
        ],
        "account_location_sharing": [],
    })
    monkeypatch.setattr(database, "get_supabase", lambda: db)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: account_id
    try:
        yield TestClient(app), db, account_id, admin_id
    finally:
        app.dependency_overrides.clear()


def test_pending_then_one_accepted_position_then_revocation(context):
    client, db, account_id, _ = context
    assert client.get("/profiles/location-sharing").json()["choice"] == "pending"

    result = client.put("/profiles/location-sharing", json={
        "choice": "accepted", "latitude": -22.91234,
        "longitude": -43.19224, "accuracy_m": 25,
    })
    assert result.status_code == 200
    assert result.json()["choice"] == "accepted"
    row = db.tables["account_location_sharing"][0]
    assert row["user_id"] == account_id
    assert row["latitude"] == -22.91
    assert row["longitude"] == -43.19
    assert row["collected_at"] is not None

    again = client.put("/profiles/location-sharing", json={
        "choice": "accepted", "latitude": -23.50, "longitude": -44.00,
    })
    assert again.status_code == 409
    assert len(db.tables["account_location_sharing"]) == 1
    assert row["latitude"] == -22.91

    revoked = client.put("/profiles/location-sharing", json={"choice": "revoked"})
    assert revoked.status_code == 200
    assert client.get("/profiles/location-sharing").json()["choice"] == "revoked"
    assert row["latitude"] is None and row["longitude"] is None and row["collected_at"] is None
    assert client.put("/profiles/location-sharing", json={
        "choice": "accepted", "latitude": -22, "longitude": -43,
    }).status_code == 409


def test_decline_persists_without_coordinates(context):
    client, db, _, _ = context
    assert client.put("/profiles/location-sharing", json={"choice": "declined"}).status_code == 200
    assert client.get("/profiles/location-sharing").json()["choice"] == "declined"
    assert db.tables["account_location_sharing"][0]["latitude"] is None
    assert client.put("/profiles/location-sharing", json={
        "choice": "accepted", "latitude": -22, "longitude": -43,
    }).status_code == 409


def test_invalid_or_unconsented_coordinates_rejected(context):
    client, db, _, _ = context
    assert client.put("/profiles/location-sharing", json={
        "choice": "accepted", "latitude": 91, "longitude": 0,
    }).status_code == 422
    assert client.put("/profiles/location-sharing", json={
        "choice": "declined", "latitude": -22,
    }).status_code == 422
    assert db.tables["account_location_sharing"] == []


def test_admin_sees_single_authorized_point_and_non_admin_cannot(context):
    client, db, account_id, admin_id = context
    client.put("/profiles/location-sharing", json={
        "choice": "accepted", "latitude": -22.9, "longitude": -43.2,
    })
    assert client.get("/admin/location-points").status_code == 403

    app.dependency_overrides[get_current_user_id] = lambda: admin_id
    result = client.get("/admin/location-points")
    assert result.status_code == 200
    points = result.json()["points"]
    assert len(points) == 1
    assert points[0]["account"] == account_id[:8]
    assert points[0]["latitude"] == -22.9
    assert points[0]["longitude"] == -43.2

    app.dependency_overrides[get_current_user_id] = lambda: account_id
    client.put("/profiles/location-sharing", json={"choice": "revoked"})
    app.dependency_overrides[get_current_user_id] = lambda: admin_id
    assert client.get("/admin/location-points").json()["points"] == []

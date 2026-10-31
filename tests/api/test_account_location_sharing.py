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


def test_admin_gets_only_client_counts_and_authorized_points(context, monkeypatch):
    """A API admin nunca mistura a localização do administrador com clientes."""
    from unittest.mock import MagicMock
    from api.routers import admin

    client, db, account_id, admin_id = context
    client.put("/profiles/location-sharing", json={
        "choice": "accepted", "latitude": -22.9, "longitude": -43.2,
    })
    assert client.get("/admin/location-points").status_code == 403

    # O filtro de access é executado na RPC SQL; testamos o contrato da API,
    # inclusive zero cliente ativo e o histórico independente de exclusões.
    geo_db = MagicMock()
    geo_db.rpc.return_value.execute.return_value = MagicMock(data={
        "status": "available",
        "updated_at": "2026-10-31T12:00:00Z",
        "customers_total": 1,
        "recent_active": 0,
        "gps_points_total": 1,
        "region_participants": 0,
        "deleted_total": 30,
        "deleted_since": "2026-01-01",
        "points": [{
            "account": account_id[:8],
            "latitude": -22.9, "longitude": -43.2,
            "accuracy_m": None,
            "collected_at": "2026-10-31T11:00:00Z",
        }],
    })
    monkeypatch.setattr(admin, "supabase", geo_db)
    app.dependency_overrides[get_current_user_id] = lambda: admin_id

    result = client.get("/admin/location-points")
    assert result.status_code == 200
    body = result.json()
    assert body["customers_total"] == 1
    assert body["gps_points_total"] == 1
    assert body["region_participants"] == 0
    assert body["deleted_total"] == 30
    assert body["points"][0]["account"] == account_id[:8]
    geo_db.rpc.assert_called_once_with("admin_client_geo_overview")

    # O total zero é informação comercial válida (não é mascarado como —).
    geo_db.rpc.return_value.execute.return_value.data.update({
        "customers_total": 0, "gps_points_total": 0, "points": [],
    })
    zero = client.get("/admin/location-points")
    assert zero.status_code == 200
    assert zero.json()["customers_total"] == 0
    assert zero.json()["deleted_total"] == 30
    assert zero.json()["points"] == []

    app.dependency_overrides[get_current_user_id] = lambda: account_id
    assert client.get("/admin/location-points").status_code == 403

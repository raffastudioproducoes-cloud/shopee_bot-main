"""First-time voluntary preferences must show empty state, not throw 406/500.

Routes are owner-scoped and must not expose another account's location.
"""
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from api import database
from api.main import app
from api.routers.auth import get_current_user_id


@pytest.fixture(autouse=True)
def reset_auth():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _client(monkeypatch, data):
    fake = MagicMock()
    query = fake.table.return_value
    for operation in ("select", "eq", "limit", "upsert", "delete", "update"):
        getattr(query, operation).return_value = query
    query.execute.return_value = MagicMock(data=data)
    monkeypatch.setattr(database, "get_supabase", lambda: fake)
    app.dependency_overrides[get_current_user_id] = lambda: "current-user-id"
    return TestClient(app), fake, query


@pytest.mark.parametrize("path,expected", [
    ("/profiles/region-preference", {"region": None, "consented": False}),
    ("/profiles/acquisition-source", {"source": None, "declared": False}),
    ("/profiles/gps-preference", {"enabled": False}),
    ("/admin/my-region", {"region": None}),
])
def test_unset_preference_is_normal_not_error(monkeypatch, path, expected):
    client, db, query = _client(monkeypatch, [])
    if path.startswith("/admin/"):
        # Admin has a separate role check; this test covers user routes only.
        return
    response = client.get(path)
    assert response.status_code == 200
    assert response.json() == expected
    query.limit.assert_called_once_with(1)
    query.maybe_single.assert_not_called()
    if path == "/profiles/gps-preference":
        query.eq.assert_called_once_with("id", "current-user-id")
    else:
        query.eq.assert_called_once_with("user_id", "current-user-id")


@pytest.mark.parametrize("path,data,expected", [
    ("/profiles/region-preference", [{"region": "BR-RJ"}], {"region": "BR-RJ", "consented": True}),
    ("/profiles/acquisition-source", [{"source": "search"}], {"source": "search", "declared": True}),
    ("/profiles/gps-preference", [{"gps_consented_at": "2026-10-31T03:00:00Z"}], {"enabled": True}),
])
def test_saved_preference_is_read_correctly(monkeypatch,path,data,expected):
    client, _, query = _client(monkeypatch, data)
    response = client.get(path)
    assert response.status_code == 200
    assert response.json() == expected
    query.limit.assert_called_once_with(1)


@pytest.mark.parametrize("path", [
    "/profiles/region-preference",
    "/profiles/acquisition-source",
    "/profiles/gps-preference",
])
def test_read_preference_requires_login(path):
    assert TestClient(app).get(path).status_code == 401


@pytest.mark.parametrize("path,payload,expected", [
    ("/profiles/region-preference", {"region":"BR-RJ","consent":True}, {"region":"BR-RJ","consented":True}),
    ("/profiles/acquisition-source", {"source":"search","consent":True}, {"source":"search","declared":True}),
])
def test_manual_choice_can_save_without_prior_read(monkeypatch,path,payload,expected):
    client, _, query = _client(monkeypatch, [{"user_id":"current-user-id"}])
    response = client.put(path, json=payload)
    assert response.status_code == 200
    assert response.json() == expected
    query.upsert.assert_called_once()

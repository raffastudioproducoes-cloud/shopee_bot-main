"""Facebook Page Insights: scoped token, real counts (including zero), safe failures."""

from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers import social_analytics
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


def _client(monkeypatch, handler, credential=None):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    seen = []

    query = MagicMock()
    query.select.return_value = query
    query.eq.side_effect = lambda key, value: (seen.append((key, value)), query)[1]
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data=credential if credential is not None else {
        "page_id": "1511578648694753", "page_access_token": "encrypted"
    })
    fake = MagicMock()
    fake.table.return_value = query
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    monkeypatch.setattr(social_analytics, "decrypt", lambda _: "private-page-token")
    monkeypatch.setattr(social_analytics, "_check_test_rate_limit", lambda _: None)

    class Client(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(social_analytics.httpx, "AsyncClient", Client)
    return TestClient(app), seen, fake


def test_facebook_insights_returns_real_daily_numbers_including_zero(monkeypatch):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path.endswith("/1511578648694753/insights")
        assert request.headers["Authorization"] == "Bearer private-page-token"
        assert request.url.params["metric"] == "page_media_view"
        assert request.url.params["period"] == "day"
        assert request.url.params["since"] and request.url.params["until"]
        return httpx.Response(200, json={
            "data": [{
                "name": "page_media_view",
                "period": "day",
                "values": [
                    {"value": 0, "end_time": "2026-10-28T07:00:00+0000"},
                    {"value": 5, "end_time": "2026-10-29T07:00:00+0000"},
                ],
            }],
            "paging": {"next": "https://example.invalid?access_token=private-page-token"},
        })

    client, seen, fake = _client(monkeypatch, handler)
    try:
        response = client.post("/analytics/probe/facebook?days=30")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "network": "facebook", "state": "ok", "metric": "page_media_view",
            "result_count": 1, "days_requested": 30, "days_returned": 2,
            "total_views": 5, "daily_values": [
                {"period_end": "2026-10-28", "value": 0},
                {"period_end": "2026-10-29", "value": 5},
            ],
        }
        assert ("user_id", 42) in seen
        assert ("profile_id", "profile-a") in seen
        assert fake.table.call_args.args == ("facebook_credentials",)
        assert "private-page-token" not in str(data)
        assert "1511578648694753" not in str(data)
    finally:
        app.dependency_overrides.clear()


def test_facebook_insights_empty_is_not_a_zero(monkeypatch):
    client, _, _ = _client(monkeypatch, lambda _: httpx.Response(200, json={"data": []}))
    try:
        data = client.post("/analytics/probe/facebook?days=7").json()
        assert data["state"] == "no_data"
        assert data["total_views"] is None
        assert data["daily_values"] == []
        assert data["days_returned"] == 0
    finally:
        app.dependency_overrides.clear()


def test_facebook_insights_rejects_unverified_counts(monkeypatch):
    client, _, _ = _client(monkeypatch, lambda _: httpx.Response(200, json={"data": [
        {"name": "page_media_view", "values": [{"value": "fake", "end_time": "2026-10-28T07:00:00+0000"}]}
    ]}))
    try:
        data = client.post("/analytics/probe/facebook").json()
        assert data == {"network": "facebook", "state": "invalid_response"}
        assert client.post("/analytics/probe/facebook?days=365").status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_facebook_insights_permissions_failure_does_not_expose_token(monkeypatch):
    client, _, _ = _client(monkeypatch, lambda _: httpx.Response(
        403, json={"error": {"message": "private-page-token", "code": 10}}
    ))
    try:
        data = client.post("/analytics/probe/facebook").json()
        assert data["state"] == "api_error"
        assert data["http_status"] == 403
        assert data["error_code"] == 10
        assert "private-page-token" not in str(data)
    finally:
        app.dependency_overrides.clear()

from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient

from api.main import app
from api import database as database_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id
from api.routers import social_analytics


def test_analytics_requires_login():
    app.dependency_overrides.clear()
    assert TestClient(app).get('/analytics/summary').status_code == 401


def test_analytics_counts_only_owned_profile_and_never_invents_social_metrics(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    seen = []

    def table(name):
        assert name == 'publish_jobs'
        query = MagicMock()
        query.select.return_value = query
        query.eq.side_effect = lambda key, value: (seen.append((key, value)), query)[1]
        query.gte.return_value = query
        query.limit.return_value = query
        query.execute.return_value = MagicMock(count=2)
        return query

    fake_client = MagicMock()
    fake_client.table.side_effect = table
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake_client)
    response = TestClient(app).get('/analytics/summary?days=7&network=threads')
    assert response.status_code == 200
    data = response.json()
    assert data['networks'][0]['network'] == 'threads'
    assert len(data['networks']) == 1
    assert data['networks'][0]['succeeded'] == 2
    assert data['networks'][0]['views'] is None
    assert ('user_id', 42) in seen
    assert ('profile_id', 'profile-a') in seen
    assert ('network', 'threads') in seen
    assert fake_client.table.call_count == 3
    app.dependency_overrides.clear()


def test_analytics_rejects_unknown_network_and_period():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    client = TestClient(app)
    assert client.get('/analytics/summary?network=kwai').status_code == 422
    assert client.get('/analytics/summary?days=999').status_code == 422
    app.dependency_overrides.clear()


def test_insights_probe_uses_owned_token_and_returns_only_safe_metadata(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    seen = []
    query = MagicMock()
    query.select.return_value = query
    query.eq.side_effect = lambda key, value: (seen.append((key, value)), query)[1]
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data={"t_user_id": "123", "access_token": "ciphertext"})
    fake_client = MagicMock()
    fake_client.table.return_value = query
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake_client)
    monkeypatch.setattr(social_analytics, "decrypt", lambda value: "private-token")
    monkeypatch.setattr(social_analytics, "_check_test_rate_limit", lambda user_id: None)

    def handler(request):
        assert request.url.host == "graph.threads.net"
        assert request.url.path == "/v1.0/123/threads_insights"
        assert request.headers["Authorization"] == "Bearer private-token"
        return httpx.Response(200, json={"data": [{"name": "views", "values": [{"value": 4}]}]})

    class Client(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(social_analytics.httpx, "AsyncClient", Client)
    response = TestClient(app).post('/analytics/probe/threads')
    assert response.status_code == 200
    result = response.json()
    assert result == {"network": "threads", "state": "ok", "metric": "views", "result_count": 1}
    assert ("user_id", 42) in seen
    assert ("profile_id", "profile-a") in seen
    assert "private-token" not in str(result)
    app.dependency_overrides.clear()

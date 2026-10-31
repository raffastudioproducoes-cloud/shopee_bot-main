from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient

from api.main import app
from api import database as database_module
from api.routers.auth import get_current_user_id
from api.routers.credentials import _require_admin
from api.routers.profiles import get_current_profile_id
from api.routers import social_analytics
from api import analytics_refresh


def test_analytics_requires_login():
    app.dependency_overrides.clear()
    assert TestClient(app).get('/analytics/summary').status_code == 401
    assert TestClient(app).post('/analytics/probe/threads').status_code == 401
    assert TestClient(app).post('/analytics/refresh').status_code == 401


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
    monkeypatch.setattr(social_analytics, '_read_refresh', lambda *args: None)

    async def skip_background(*args, **kwargs):
        return {"state": "recent"}

    monkeypatch.setattr(social_analytics, 'refresh_account', skip_background)
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


def test_insights_probe_rejects_common_users_without_calling_provider(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data={'access': 'USER'})
    fake_client = MagicMock()
    fake_client.table.return_value = query
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake_client)
    try:
        response = TestClient(app).post('/analytics/probe/threads')
        assert response.status_code == 403
        fake_client.table.assert_called_once_with('users')
    finally:
        app.dependency_overrides.clear()


def test_insights_probe_uses_owned_token_and_returns_only_safe_metadata(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[_require_admin] = lambda: 42
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


def test_manual_refresh_scoped_to_logged_in_profile(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    called = []

    async def fake_refresh(user_id, profile_id, *, manual=False):
        called.append((user_id, profile_id, manual))
        return {"state": "updated", "provider_states": {"facebook": "not_connected"}}

    monkeypatch.setattr(social_analytics, "refresh_account", fake_refresh)
    try:
        response = TestClient(app).post('/analytics/refresh')
        assert response.status_code == 200
        assert response.json()["state"] == "updated"
        assert called == [('user-a', 'profile-a', True)]
    finally:
        app.dependency_overrides.clear()


def test_refresh_requires_active_profile(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: None
    try:
        assert TestClient(app).post('/analytics/refresh').status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_facebook_cached_daily_values_never_fill_missing_days():
    cached = {"provider_states": {"facebook": "ok"},
              "facebook_daily_values": [
                  {"period_end": "2999-01-01", "value": 7},
                  {"period_end": "2999-01-02", "value": 0},
              ]}
    assert social_analytics._facebook_views_for_period(cached, 7) == 7
    cached["provider_states"] = {"facebook": "api_error"}
    assert social_analytics._facebook_views_for_period(cached, 7) is None
    cached["provider_states"] = {"facebook": "ok"}
    cached["facebook_daily_values"][0]["value"] = True
    assert social_analytics._facebook_views_for_period(cached, 7) is None


def test_collector_parses_only_valid_metrics():
    metrics = [{"name": "views", "total_value": {"value": 33}}]
    assert analytics_refresh._threads_views(metrics) == 33
    assert analytics_refresh._threads_views([{"name": "views", "values": [
        {"value": 10}, {"value": 10}
    ]}]) is None
    assert analytics_refresh._threads_views([{"name": "views", "total_value": {"value": True}}]) is None
    daily = [{"name": "page_media_view", "values": [
        {"value": 0, "end_time": "2026-10-30T00:00:00+0000"},
    ]}]
    assert analytics_refresh._facebook_daily_values(daily) == [
        {"period_end": "2026-10-30", "value": 0}
    ]


def test_collector_credentials_restricted_by_user_and_profile(monkeypatch):
    fields = []
    query = MagicMock()
    query.select.return_value = query
    query.eq.side_effect = lambda key, value: (fields.append((key, value)), query)[1]
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data={"page_id": "page-a", "page_access_token": "cipher"})
    fake = MagicMock()
    fake.table.return_value = query
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    assert analytics_refresh._credential("user-a", "profile-a", "facebook") == ("page-a", "cipher")
    assert ("user_id", "user-a") in fields
    assert ("profile_id", "profile-a") in fields
    assert "cipher" not in str(fields)


def test_collector_does_not_repeat_when_claim_unavailable(monkeypatch):
    import asyncio
    monkeypatch.setattr(analytics_refresh, "_claim", lambda *args: None)
    async def forbidden(*args, **kwargs):
        raise AssertionError("não deve chamar API externa sem claim")
    monkeypatch.setattr(analytics_refresh, "_fetch_network", forbidden)
    assert asyncio.run(analytics_refresh.refresh_account("user-a", "profile-a")) == {"state": "recent"}



def test_analytics_timeline_requires_login_and_rejects_invalid_filters():
    app.dependency_overrides.clear()
    client = TestClient(app)
    assert client.get('/analytics/timeline').status_code == 401
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    try:
        assert client.get('/analytics/timeline?days=15').status_code == 422
        assert client.get('/analytics/timeline?network=kwai').status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_analytics_timeline_aggregates_only_authenticated_profile(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    rpc_query = MagicMock()
    rpc_query.execute.return_value = MagicMock(data=[
        {'day': '2026-10-30', 'network': 'threads', 'status': 'succeeded', 'total': 3},
        {'day': '2026-10-31', 'network': 'threads', 'status': 'failed', 'total': 1},
    ])
    fake = MagicMock()
    fake.rpc.return_value = rpc_query
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    try:
        result = TestClient(app).get('/analytics/timeline?days=7&network=threads')
        assert result.status_code == 200
        assert result.json()['points'][0]['total'] == 3
        assert result.json()['points'][1]['status'] == 'failed'
        fake.rpc.assert_called_once_with('analytics_daily_job_counts', {
            'p_user_id': 'user-a', 'p_profile_id': 'profile-a',
            'p_days': 7, 'p_network': 'threads',
        })
    finally:
        app.dependency_overrides.clear()


def test_analytics_timeline_without_profile_never_queries_database(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: None
    fake = MagicMock()
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    try:
        result = TestClient(app).get('/analytics/timeline?days=30')
        assert result.status_code == 200
        assert result.json() == {'days': 30, 'points': []}
        fake.rpc.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_analytics_timeline_does_not_expose_database_errors(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    fake = MagicMock()
    fake.rpc.side_effect = RuntimeError('internal database connection')
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    try:
        result = TestClient(app).get('/analytics/timeline')
        assert result.status_code == 503
        assert 'internal database connection' not in result.text
    finally:
        app.dependency_overrides.clear()

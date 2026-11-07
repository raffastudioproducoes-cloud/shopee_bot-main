from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from api import database as database_module
from api.routers.auth import get_current_user_id
from api.routers.credentials import _require_admin
from api.routers.profiles import get_current_profile_id
from api.routers import social_analytics
from api import analytics_refresh
from api import post_insights


def _no_post_insights(monkeypatch, *, connected=True):
    monkeypatch.setattr(social_analytics, 'published_jobs', lambda *args: [])
    monkeypatch.setattr(social_analytics, 'indexed_insights', lambda *args: {})
    monkeypatch.setattr(social_analytics, 'current_network_connections',
                        lambda *args: {'threads': connected, 'facebook': False, 'instagram': False})


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
    _no_post_insights(monkeypatch)

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


def test_insights_probe_uses_only_cached_owned_post_not_account_insights(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[_require_admin] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    monkeypatch.setattr(social_analytics, "_check_test_rate_limit", lambda user_id: None)
    monkeypatch.setattr(social_analytics, 'published_jobs', lambda *args: [{
        'id': 'job-1', 'network': 'threads', 'external_id': '123'}])
    monkeypatch.setattr(social_analytics, 'indexed_insights', lambda *args: {
        'job-1': {'external_id': '123', 'state': 'ok', 'views': 4}})
    response = TestClient(app).post('/analytics/probe/threads')
    assert response.status_code == 200
    result = response.json()
    assert result == {"network": "threads", "state": "ok", "metric": "views", "post_count": 1, "total_views": 4}
    app.dependency_overrides.clear()


def test_manual_refresh_scoped_to_logged_in_profile(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    called = []

    def fake_claim(user_id, profile_ids):
        assert (user_id, profile_ids) == ('user-a', ['profile-a'])
        return {'state': 'accepted', 'claims': {'profile-a': 'claim-secret'},
                'quota': {'unlimited': False, 'used': 1, 'limit': 10, 'remaining': 9}}

    async def fake_refresh(user_id, profile_id, *, manual=False, claim_token=None):
        called.append((user_id, profile_id, manual, claim_token))
        return {"state": "updated", "provider_states": {"facebook": "not_connected"}}

    monkeypatch.setattr(social_analytics, 'claim_manual_refresh', fake_claim)
    monkeypatch.setattr(social_analytics, "refresh_account", fake_refresh)
    try:
        response = TestClient(app).post('/analytics/refresh')
        assert response.status_code == 200
        assert response.json()["state"] == "updated"
        assert response.json()['quota']['remaining'] == 9
        assert called == [('user-a', 'profile-a', True, 'claim-secret')]
        assert 'claim-secret' not in response.text
    finally:
        app.dependency_overrides.clear()


def test_manual_refresh_all_profiles_claims_once_for_the_account(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    claims = []
    refreshed = []
    monkeypatch.setattr(social_analytics, '_account_profile_ids', lambda user_id: ['profile-a', 'profile-b'])

    def fake_claim(user_id, ids):
        claims.append((user_id, ids))
        return {'state': 'accepted', 'claims': {'profile-a': 'tok-a', 'profile-b': 'tok-b'},
                'quota': {'unlimited': False, 'used': 1, 'remaining': 9, 'limit': 10}}

    async def fake_refresh(user_id, profile_id, *, manual=False, claim_token=None):
        refreshed.append((user_id, profile_id, manual, claim_token))
        return {'state': 'updated'}

    monkeypatch.setattr(social_analytics, 'claim_manual_refresh', fake_claim)
    monkeypatch.setattr(social_analytics, 'refresh_account', fake_refresh)
    try:
        result = TestClient(app).post('/analytics/refresh?profile_id=all')
        assert result.status_code == 200
        assert result.json()['updated_profiles'] == 2
        assert claims == [('user-a', ['profile-a', 'profile-b'])]
        assert sorted(refreshed) == [
            ('user-a', 'profile-a', True, 'tok-a'), ('user-a', 'profile-b', True, 'tok-b')]
        assert 'tok-a' not in result.text and 'tok-b' not in result.text
    finally:
        app.dependency_overrides.clear()


def test_manual_refresh_limit_returns_429_without_collecting(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    monkeypatch.setattr(social_analytics, 'claim_manual_refresh', lambda *args: {
        'state': 'limit_reached',
        'quota': {'unlimited': False, 'used': 10, 'remaining': 0, 'limit': 10}})

    async def forbidden(*args, **kwargs):
        raise AssertionError('quota excedida não pode acionar provedor')

    monkeypatch.setattr(social_analytics, 'refresh_account', forbidden)
    try:
        result = TestClient(app).post('/analytics/refresh')
        assert result.status_code == 429
        assert 'Limite de 10' in result.json()['detail']
    finally:
        app.dependency_overrides.clear()


def test_manual_refresh_in_cooldown_does_not_consume_quota(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'profile-a'
    monkeypatch.setattr(social_analytics, 'claim_manual_refresh', lambda *args: {
        'state': 'recent',
        'quota': {'unlimited': False, 'used': 1, 'remaining': 9, 'limit': 10}})
    try:
        result = TestClient(app).post('/analytics/refresh')
        assert result.status_code == 200
        assert result.json()['state'] == 'recent'
        assert result.json()['quota']['remaining'] == 9
    finally:
        app.dependency_overrides.clear()


def test_manual_quota_status_admin_unlimited_and_normal_limit(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    monkeypatch.setattr(social_analytics, 'manual_quota_status', lambda user_id: {
        'unlimited': True, 'used': 0, 'remaining': None, 'limit': None,
        'reset_at': '2026-11-08T03:00:00Z'})
    try:
        result = TestClient(app).get('/analytics/refresh/quota')
        assert result.status_code == 200
        assert result.json()['unlimited'] is True
        assert result.json()['remaining'] is None
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


def test_account_views_are_never_treated_as_post_metrics():
    jobs = [{'id': 'a', 'network': 'threads', 'external_id': '111'}]
    result, collected, eligible, states = post_insights.summarize_post_metrics(jobs, {
        'a': {'network': 'facebook', 'external_id': '111', 'state': 'ok', 'views': 31}})
    assert result['views'] is None
    assert collected == 0 and eligible == 1 and states == {'not_collected'}


def test_collector_parses_only_valid_metrics():
    metrics = [{"name": "views", "total_value": {"value": 33}},
               {"name": "likes", "values": [{"value": 0}]}]
    parsed = post_insights.parse_threads_post_insights(metrics)
    assert parsed['views'] == 33 and parsed['likes'] == 0
    assert parsed['clicks'] is None
    assert post_insights.parse_threads_post_insights([{"name": "views", "values": [
        {"value": 10}, {"value": 10}
    ]}]) is None
    assert post_insights.parse_threads_post_insights([{"name": "views", "total_value": {"value": True}}]) is None


def test_collector_credentials_restricted_by_user_and_profile(monkeypatch):
    fields = []
    query = MagicMock()
    query.select.return_value = query
    query.eq.side_effect = lambda key, value: (fields.append((key, value)), query)[1]
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data={"t_user_id": "123", "access_token": "cipher", "status": True})
    fake = MagicMock()
    fake.table.return_value = query
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    assert post_insights._threads_credential("user-a", "profile-a") == "cipher"
    assert ("user_id", "user-a") in fields
    assert ("profile_id", "profile-a") in fields
    assert "cipher" not in str(fields)


def test_collector_does_not_repeat_when_claim_unavailable(monkeypatch):
    import asyncio
    monkeypatch.setattr(analytics_refresh, "_claim", lambda *args: None)
    async def forbidden(*args, **kwargs):
        raise AssertionError("não deve chamar API externa sem claim")
    monkeypatch.setattr(analytics_refresh, "collect_profile_posts", forbidden)
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


def test_analytics_all_profiles_counts_account_history_without_reading_credentials(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'active-id'
    filters = []

    def account_jobs_query(name):
        assert name == 'publish_jobs'
        query = MagicMock()
        query.select.return_value = query
        query.eq.side_effect = lambda k, v: (filters.append((k, v)), query)[1]
        query.gte.return_value = query
        query.limit.return_value = query
        query.execute.return_value = MagicMock(count=2)
        return query

    fake = MagicMock()
    fake.table.side_effect = account_jobs_query
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    monkeypatch.setattr(social_analytics, '_read_refresh', lambda *args: 1 / 0)
    monkeypatch.setattr(social_analytics, '_account_profile_ids', lambda *args: [])
    _no_post_insights(monkeypatch)

    async def forbidden(*args, **kwargs):
        raise AssertionError('all não dispara OAuth/coleta em massa')

    monkeypatch.setattr(social_analytics, 'refresh_account', forbidden)
    try:
        result = TestClient(app).get('/analytics/summary?profile_id=all&days=7&network=threads')
        assert result.status_code == 200
        body = result.json()
        assert body['networks'] == [{
            'network': 'threads', 'succeeded': 2, 'failed': 2, 'unknown': 2,
            'views': None, 'likes': None, 'comments': None, 'reposts': None,
            'clicks': None, 'shares': None, 'quotes': None, 'insights_status': 'no_posts',
            'posts_with_insights': 0, 'posts_with_external_id': 0,
        }]
        assert ('user_id', 'user-a') in filters
        assert all(name != 'profile_id' for name, _ in filters)
        assert fake.table.call_count == 3
    finally:
        app.dependency_overrides.clear()


def test_analytics_selected_profile_requires_ownership_without_activating_it(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'active-id'
    selected = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
    seen = []

    def table(name):
        query = MagicMock()
        query.select.return_value = query
        query.eq.side_effect = lambda k, v: (seen.append((name, k, v)), query)[1]
        query.maybe_single.return_value = query
        query.execute.return_value = MagicMock(data={'id': selected} if name == 'profiles' else None, count=1)
        query.gte.return_value = query
        query.limit.return_value = query
        return query

    fake = MagicMock()
    fake.table.side_effect = table
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    monkeypatch.setattr(social_analytics, '_read_refresh', lambda *args: None)
    _no_post_insights(monkeypatch)

    async def skip_background(*args, **kwargs):
        return {'state': 'recent'}

    monkeypatch.setattr(social_analytics, 'refresh_account', skip_background)
    try:
        result = TestClient(app).get(f'/analytics/summary?days=7&network=threads&profile_id={selected}')
        assert result.status_code == 200
        assert ('profiles', 'user_id', 'user-a') in seen
        assert ('profiles', 'id', selected) in seen
        assert ('publish_jobs', 'user_id', 'user-a') in seen
        assert ('publish_jobs', 'profile_id', selected) in seen
        assert ('publish_jobs', 'profile_id', 'active-id') not in seen
    finally:
        app.dependency_overrides.clear()


def test_analytics_foreign_or_invalid_profile_is_rejected_before_jobs(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'active-id'
    fake = MagicMock()
    owned_query = MagicMock()
    owned_query.select.return_value = owned_query
    owned_query.eq.return_value = owned_query
    owned_query.maybe_single.return_value = owned_query
    owned_query.execute.return_value = MagicMock(data=None)
    fake.table.return_value = owned_query
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    try:
        client = TestClient(app)
        assert client.get('/analytics/summary?profile_id=not-a-uuid').status_code == 422
        assert client.get('/analytics/summary?profile_id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb').status_code == 404
        assert client.get('/analytics/timeline?profile_id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb').status_code == 404
        assert client.post('/analytics/refresh?profile_id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb').status_code == 404
        assert all(call.args[0] == 'profiles' for call in fake.table.call_args_list)
    finally:
        app.dependency_overrides.clear()


def test_analytics_all_timeline_includes_archived_and_unassigned_without_duplicates(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'active-id'
    first = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
    archived = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
    filters = []
    sorts = []
    rpc_calls = []

    def query_for(name):
        query = MagicMock()
        query.select.return_value = query
        query.eq.side_effect = lambda k, v: (filters.append((name, k, v)), query)[1]
        query.is_.side_effect = lambda k, v: (filters.append((name, k, v)), query)[1]
        query.in_.return_value = query
        query.gte.return_value = query
        query.order.side_effect = lambda field: (sorts.append(field), query)[1]
        query.range.return_value = query
        if name == 'profiles':
            query.execute.return_value = MagicMock(data=[{'id': first}, {'id': archived}])
        else:
            query.execute.return_value = MagicMock(data=[{
                'id': 9, 'network': 'threads', 'status': 'succeeded',
                'finished_at': '2026-11-05T14:00:00+00:00',
            }])
        return query

    fake = MagicMock()
    fake.table.side_effect = query_for

    def rpc(name, args):
        rpc_calls.append((name, args))
        result = MagicMock()
        result.execute.return_value = MagicMock(data=[{
            'day': '2026-11-05', 'network': 'threads', 'status': 'succeeded', 'total': 2,
        }])
        return result

    fake.rpc.side_effect = rpc
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    try:
        result = TestClient(app).get('/analytics/timeline?profile_id=all&days=30&network=threads')
        assert result.status_code == 200
        assert result.json()['points'] == [{
            'day': '2026-11-05', 'network': 'threads', 'status': 'succeeded', 'total': 5,
        }]
        assert len(rpc_calls) == 2
        assert {args['p_profile_id'] for _, args in rpc_calls} == {first, archived}
        assert all(args['p_user_id'] == 'user-a' for _, args in rpc_calls)
        assert ('profiles', 'user_id', 'user-a') in filters
        assert ('publish_jobs', 'user_id', 'user-a') in filters
        assert ('publish_jobs', 'profile_id', 'null') in filters
        assert sorts[-2:] == ['finished_at', 'id']
    finally:
        app.dependency_overrides.clear()


def test_analytics_missing_count_is_not_reported_as_zero(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'active-id'
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.gte.return_value = query
    query.limit.return_value = query
    query.execute.return_value = MagicMock(count=None)
    fake = MagicMock()
    fake.table.return_value = query
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    monkeypatch.setattr(social_analytics, '_read_refresh', lambda *args: None)
    monkeypatch.setattr(social_analytics, '_account_profile_ids', lambda *args: [])
    _no_post_insights(monkeypatch)
    try:
        result = TestClient(app).get('/analytics/summary?profile_id=all&network=threads')
        assert result.status_code == 503
        assert 'temporariamente indisponível' in result.text
    finally:
        app.dependency_overrides.clear()


def test_analytics_refresh_explicit_owned_profile_without_mass_refresh(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 'user-a'
    app.dependency_overrides[get_current_profile_id] = lambda: 'active-id'
    selected = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.maybe_single.return_value = query
    query.execute.return_value = MagicMock(data={'id': selected})
    fake = MagicMock()
    fake.table.return_value = query
    monkeypatch.setattr(database_module, 'get_supabase', lambda: fake)
    called = []

    async def fake_refresh(user_id, profile_id, *, manual=False):
        called.append((user_id, profile_id, manual))
        return {'state': 'updated'}

    monkeypatch.setattr(social_analytics, 'refresh_account', fake_refresh)
    try:
        client = TestClient(app)
        assert client.post('/analytics/refresh?profile_id=all').status_code == 400
        result = client.post(f'/analytics/refresh?profile_id={selected}')
        assert result.status_code == 200
        assert called == [('user-a', selected, True)]
    finally:
        app.dependency_overrides.clear()

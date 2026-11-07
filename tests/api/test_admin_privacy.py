from fastapi.testclient import TestClient
from api import database
from api.main import app
from api.routers.auth import get_current_user_id
from api.routers import credentials
from api.admin_views import AdminLogEntry


def test_unknown_route_and_http_method_cannot_expose_free_text():
    entry = AdminLogEntry(method='private-method', path='/unknown/private-value?token=private-token', created_at='2026-10-15T06:00:00')
    assert entry.method == 'OUTRO'
    assert entry.path == 'Rota não identificada'
    assert 'private' not in entry.model_dump_json()
    assert entry.created_at.tzinfo is not None


def test_credential_diagnostic_actions_have_useful_whitelisted_log_labels():
    stamp = '2026-11-07T12:00:00Z'
    assert AdminLogEntry(method='ACTION', path='admin_credentials_test_shopee_ok',
                         created_at=stamp).path == 'Diagnóstico: Shopee — funcionando'
    assert AdminLogEntry(method='ACTION', path='admin_credentials_test_x_error',
                         created_at=stamp).path == 'Diagnóstico: X — falha'
    assert AdminLogEntry(method='ACTION', path='admin_credentials_test_all',
                         created_at=stamp).path == 'Diagnóstico: teste geral de conexões'
    assert AdminLogEntry(method='ACTION', path='admin_credentials_test_secret_ok',
                         created_at=stamp).path == 'Rota não identificada'


def test_admin_connection_status_omits_provider_diagnostics(monkeypatch, fake_db):
    db = fake_db({'users': [{'id': 'owner', 'access': 'ADMIN'}]})
    monkeypatch.setattr(database, 'get_supabase', lambda: db)
    app.dependency_overrides[get_current_user_id] = lambda: 'owner'
    app.dependency_overrides[credentials.list_credentials] = lambda: {'threads': dict(
        connected=True, light='yellow', state='error', checked_at=None,
        check_message='private-provider-token', status_text='private-provider-token')}
    try:
        response = TestClient(app).get('/admin/credentials/status')
        assert response.status_code == 200
        assert 'private-provider-token' not in response.text
        assert 'check_message' not in response.text
        assert response.json()['threads']['status_text'] == 'Falha no teste de conexão'
    finally:
        app.dependency_overrides.clear()


def test_admin_logs_only_expose_operational_fields(monkeypatch, fake_db):
    private = 'd659d068-35e7-4fa3-a0a5-2151d9fd0011'
    row = dict(id=42, user_id=private, profile_id=private, username='private-person',
               method='GET', path=f'/admin/users/{private}?token=private-token', action='private action',
               status_code=200, duration_ms=20, error='private diagnostic',
               redirect_to='https://private.example', client_ip='192.0.2.9', created_at='2026-10-15T06:00:00')
    db = fake_db({'users': [{'id': 'owner', 'access': 'ADMIN'}], 'request_logs': [row]})
    monkeypatch.setattr(database, 'get_supabase', lambda: db)
    app.dependency_overrides[get_current_user_id] = lambda: 'owner'
    try:
        response = TestClient(app).get('/admin/logs')
        assert response.status_code == 200
        entry = response.json()['data'][0]
        assert set(entry) == {'method', 'path', 'status_code', 'duration_ms', 'created_at'}
        assert entry['path'] == '/admin/users/{user_id}'
        for marker in [private, 'private-person', 'private-token', 'private diagnostic', '192.0.2.9']:
            assert marker not in response.text
    finally:
        app.dependency_overrides.clear()

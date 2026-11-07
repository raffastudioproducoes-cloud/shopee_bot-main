"""Contrato atual: análises do Facebook só usam cache de posts confirmados.

Métricas gerais de Página, tokens e endpoints de /{page}/insights não
participam do probe; isso evita atribuir visualizações da Página a um post.
"""

from fastapi.testclient import TestClient

from api.main import app
from api.routers import social_analytics
from api.routers.auth import get_current_user_id
from api.routers.credentials import _require_admin
from api.routers.profiles import get_current_profile_id


def _client(monkeypatch, jobs, insights):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[_require_admin] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    seen = []
    monkeypatch.setattr(social_analytics, "_check_test_rate_limit", lambda _: None)
    monkeypatch.setattr(social_analytics, "published_jobs", lambda *args: (
        seen.append(args), jobs
    )[1])
    monkeypatch.setattr(social_analytics, "indexed_insights", lambda *args: insights)
    return TestClient(app), seen


def test_facebook_probe_reads_only_cached_post_insights_including_zero(monkeypatch):
    client, seen = _client(monkeypatch, [
        {"id": "job-fb", "network": "facebook", "external_id": "222"},
    ], {
        "job-fb": {"network": "facebook", "external_id": "222", "state": "ok", "views": 0},
    })
    try:
        response = client.post("/analytics/probe/facebook?days=30")
        assert response.status_code == 200
        assert response.json() == {
            "network": "facebook", "state": "ok", "post_count": 1,
            "metric": "views", "total_views": 0,
        }
        assert seen == [(42, "profile-a", 30, "facebook")]
        assert "page_id" not in str(response.json())
        assert "access_token" not in str(response.json())
    finally:
        app.dependency_overrides.clear()


def test_facebook_probe_without_confirmed_posts_does_not_invent_zero(monkeypatch):
    client, _ = _client(monkeypatch, [], {})
    try:
        data = client.post("/analytics/probe/facebook?days=7").json()
        assert data == {"network": "facebook", "state": "no_posts", "post_count": 0}
        assert "total_views" not in data
    finally:
        app.dependency_overrides.clear()


def test_facebook_probe_rejects_unverified_post_identity(monkeypatch):
    client, _ = _client(monkeypatch, [
        {"id": "job-fb", "network": "facebook", "external_id": "222"},
    ], {
        "job-fb": {"external_id": "other-post", "state": "ok", "views": 99999},
    })
    try:
        data = client.post("/analytics/probe/facebook").json()
        assert data == {"network": "facebook", "state": "not_collected", "post_count": 1}
        assert client.post("/analytics/probe/facebook?days=365").status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_facebook_probe_reports_cache_failure_without_exposing_tokens(monkeypatch):
    client, _ = _client(monkeypatch, [
        {"id": "job-fb", "network": "facebook", "external_id": "222"},
    ], {
        "job-fb": {"external_id": "222", "state": "permission_required",
                   "views": None, "access_token": "private-page-token"},
    })
    try:
        data = client.post("/analytics/probe/facebook").json()
        assert data == {
            "network": "facebook", "state": "permission_required",
            "post_count": 1, "metric": "views", "total_views": None,
        }
        assert "private-page-token" not in str(data)
    finally:
        app.dependency_overrides.clear()

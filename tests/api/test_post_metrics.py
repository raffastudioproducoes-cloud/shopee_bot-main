"""Fase 1 de métricas por post: leitura (ownership/filtros/limites), coletor com histórico
e redirecionador de cliques. Nenhuma chamada de rede real: Supabase e Threads são fakes."""
import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import database as database_module
from api import post_insights
from api.main import app
from api.routers import link_redirect, post_metrics
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id

NOW = datetime.now(timezone.utc)
RECENT = (NOW - timedelta(days=2)).isoformat()
OLD = (NOW - timedelta(days=200)).isoformat()


def _job(job_id, user, profile, network="threads", finished=RECENT, external="111", post_id=1):
    return {"id": job_id, "user_id": user, "profile_id": profile, "post_id": post_id, "network": network,
            "status": "succeeded", "finished_at": finished, "external_id": external}


def _insight(job_id, user, network="threads", external="111", state="ok", **metrics):
    return {"publish_job_id": job_id, "user_id": user, "network": network, "external_id": external,
            "state": state, "last_completed_at": RECENT, **metrics}


@pytest.fixture
def db(fake_db, monkeypatch):
    store = fake_db({
        "profiles": [{"id": "00000000-0000-0000-0000-0000000000a1", "user_id": "user-a"},
                     {"id": "00000000-0000-0000-0000-0000000000b1", "user_id": "user-b"}],
        "publish_jobs": [
            _job("job-a1", "user-a", "00000000-0000-0000-0000-0000000000a1", external="111", post_id=1),
            _job("job-a2", "user-a", "00000000-0000-0000-0000-0000000000a1", network="x", external="222", post_id=2),
            _job("job-a3", "user-a", "00000000-0000-0000-0000-0000000000a1", external="333", post_id=3),
            _job("job-old", "user-a", "00000000-0000-0000-0000-0000000000a1", finished=OLD, external="444", post_id=4),
            _job("job-b1", "user-b", "00000000-0000-0000-0000-0000000000b1", external="999", post_id=9),
        ],
        "publication_insights": [
            _insight("job-a1", "user-a", views=50, likes=3, comments=1, shares=2, reposts=1),
            _insight("job-a2", "user-a", network="x", external="222", views=80, likes=None),
            _insight("job-a3", "user-a", external="333", state="multipart_unmapped", views=7),
            _insight("job-old", "user-a", external="444", views=1000),
            _insight("job-b1", "user-b", external="999", views=99999),
        ],
        "post_link_clicks": [
            {"publish_job_id": "job-a1", "user_id": "user-a", "network": "threads", "token": "t" * 22, "clicks": 4},
            {"publish_job_id": "job-b1", "user_id": "user-b", "network": "threads", "token": "u" * 22, "clicks": 500},
        ],
        "posts": [{"id": 1, "user_id": "user-a", "text": "Oferta A"}, {"id": 9, "user_id": "user-b", "text": "segredo B"}],
        "post_metrics": [],
    })
    table_cls = type(store.table("posts"))

    def gte(self, field, value):  # o fake compartilhado ignora gte; aqui o período importa
        self._preds.append(lambda r: r.get(field) is not None and str(r.get(field)) >= str(value))
        return self
    monkeypatch.setattr(table_cls, "gte", gte, raising=False)
    monkeypatch.setattr(database_module, "get_supabase", lambda: store)
    app.dependency_overrides[get_current_user_id] = lambda: "user-a"
    app.dependency_overrides[get_current_profile_id] = lambda: "00000000-0000-0000-0000-0000000000a1"
    yield store
    app.dependency_overrides.clear()


def test_endpoints_require_login():
    app.dependency_overrides.clear()
    client = TestClient(app)
    for path in ("/analytics/post-metrics", "/analytics/ranking", "/analytics/series"):
        assert client.get(path).status_code == 401


def test_list_only_returns_own_posts_with_null_for_unavailable(db):
    body = TestClient(app).get("/analytics/post-metrics?profile_id=all&days=30").json()
    ids = [post["job_id"] for post in body["posts"]]
    assert ids == ["job-a2", "job-a1", "job-a3"]  # views desc; old job fora do período
    assert "job-b1" not in ids and "segredo B" not in str(body)
    a1 = next(post for post in body["posts"] if post["job_id"] == "job-a1")
    assert (a1["views"], a1["shares"], a1["clicks"], a1["preview"]) == (50, 3, 4, "Oferta A")
    a2 = next(post for post in body["posts"] if post["job_id"] == "job-a2")
    assert a2["likes"] is None and a2["clicks"] is None and a2["reach"] is None
    a3 = next(post for post in body["posts"] if post["job_id"] == "job-a3")
    assert a3["status"] == "parcial" and a3["views"] == 7


def test_longer_period_and_network_filter(db):
    client = TestClient(app)
    ids = [p["job_id"] for p in client.get("/analytics/post-metrics?profile_id=all&days=365").json()["posts"]]
    assert "job-old" in ids
    only_x = client.get("/analytics/post-metrics?profile_id=all&days=30&network=x").json()["posts"]
    assert [p["job_id"] for p in only_x] == ["job-a2"]


def test_other_users_profile_is_404(db):
    response = TestClient(app).get("/analytics/post-metrics?profile_id=00000000-0000-0000-0000-0000000000b1")
    assert response.status_code == 404


@pytest.mark.parametrize("query", [
    "days=999", "days=60", "from=2025-01-01&to=2026-01-02", "from=2026-02-01&to=2026-01-01",
    "from=2026-01-01", "tz=Marte/Base", "limit=0", "limit=101", "network=kwai", "sort=reach",
])
def test_invalid_parameters_are_422(db, query):
    assert TestClient(app).get(f"/analytics/post-metrics?{query}").status_code == 422


def test_custom_range_up_to_365_days_is_accepted(db):
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=364)
    response = TestClient(app).get(f"/analytics/post-metrics?profile_id=all&from={start}&to={end}&tz=UTC")
    assert response.status_code == 200 and response.json()["period"]["days"] == 365


def test_pagination_is_bounded(db):
    body = TestClient(app).get("/analytics/post-metrics?profile_id=all&days=30&limit=1&offset=1").json()
    assert [p["job_id"] for p in body["posts"]] == ["job-a1"] and body["total"] == 3


def test_ranking_posts_and_networks(db):
    body = TestClient(app).get("/analytics/ranking?profile_id=all&days=30&metric=views&top=2").json()
    assert [p["job_id"] for p in body["posts"]] == ["job-a2", "job-a1"]
    threads = next(item for item in body["networks"] if item["network"] == "threads")
    assert threads["total"] == 57 and threads["posts_measured"] == 2 and threads["average"] == 28.5
    clicks = TestClient(app).get("/analytics/ranking?profile_id=all&days=30&metric=clicks").json()
    assert [p["job_id"] for p in clicks["posts"]] == ["job-a1"]
    assert TestClient(app).get("/analytics/ranking?metric=reach").status_code == 422
    assert TestClient(app).get("/analytics/ranking?top=51").status_code == 422


def test_series_aggregates_history_and_blocks_foreign_job(db):
    day1 = (NOW - timedelta(days=2)).replace(hour=12).isoformat()
    day2 = (NOW - timedelta(days=1)).replace(hour=12).isoformat()
    db.tables["post_metrics"].extend([
        {"id": 1, "user_id": "user-a", "profile_id": "p", "publish_job_id": "job-a1", "network": "threads",
         "collected_at": day1, "status": "ok", "views": 10, "likes": None, "comments": None, "shares": None},
        {"id": 2, "user_id": "user-a", "profile_id": "p", "publish_job_id": "job-a1", "network": "threads",
         "collected_at": day2, "status": "ok", "views": 30, "likes": None, "comments": None, "shares": None},
        {"id": 3, "user_id": "user-b", "profile_id": "q", "publish_job_id": "job-b1", "network": "threads",
         "collected_at": day2, "status": "ok", "views": 999, "likes": 1, "comments": 1, "shares": 1},
    ])
    body = TestClient(app).get("/analytics/series?profile_id=all&days=7&tz=UTC").json()
    views = [point["views"] for point in body["points"]]
    assert 999 not in views and views[-1] == 30 and 10 in views
    assert TestClient(app).get(
        "/analytics/series?job_id=00000000-0000-0000-0000-00000000dead").status_code == 404


def test_daily_series_carries_last_value_forward():
    zone = ZoneInfo("UTC")
    begin = datetime(2026, 11, 1, tzinfo=timezone.utc)
    rows = [{"network": "threads", "publish_job_id": "a", "collected_at": "2026-11-01T10:00:00+00:00", "views": 5},
            {"network": "threads", "publish_job_id": "b", "collected_at": "2026-11-02T10:00:00+00:00", "views": 3}]
    points = post_metrics.daily_series(rows, begin, 3, zone)
    assert [p["views"] for p in points] == [5, 8, 8]


def test_resolve_period_limits():
    zone = ZoneInfo("UTC")
    today = date(2026, 11, 12)
    assert post_metrics.resolve_period(None, None, None, zone, today)[2] == 30
    assert post_metrics.resolve_period(365, None, None, zone, today)[2] == 365
    with pytest.raises(HTTPException):
        post_metrics.resolve_period(None, date(2026, 11, 1), date(2026, 11, 13), zone, today)


# ---------------- Coletor ----------------

def _collector(monkeypatch, jobs, handler, multi=frozenset()):
    persisted, history = [], []
    monkeypatch.setattr(post_insights, "_profile_jobs", lambda *a: jobs)
    monkeypatch.setattr(post_insights, "_threads_account", lambda *a: ("17841400000000000", "cipher"))
    monkeypatch.setattr(post_insights, "decrypt", lambda value: "secret-token")
    monkeypatch.setattr(post_insights, "_multi_part_ids", lambda *a: set(multi))
    monkeypatch.setattr(post_insights, "_persist", lambda job, user, state, metrics: persisted.append((job["id"], state, metrics)))
    monkeypatch.setattr(post_insights, "_record_history", history.append)
    real = httpx.AsyncClient
    monkeypatch.setattr(post_insights.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    asyncio.run(post_insights.collect_profile_posts("user-a", "profile-a"))
    return persisted, history


def test_collector_appends_history_on_success_and_error_without_token(monkeypatch):
    def handler(request):
        if "/222/" in request.url.path:
            return httpx.Response(500, json={"error": {"message": "secret-token leaked?"}})
        return httpx.Response(200, json={"data": [{"name": "views", "total_value": {"value": 12}},
                                                  {"name": "reposts", "total_value": {"value": 2}}]})
    jobs = [_job("j1", "user-a", "profile-a", external="111"), _job("j2", "user-a", "profile-a", external="222", post_id=2)]
    persisted, history = _collector(monkeypatch, jobs, handler)
    rows = {row["publish_job_id"]: row for row in history}
    assert rows["j1"]["status"] == "ok" and rows["j1"]["views"] == 12 and rows["j1"]["shares"] == 2
    assert rows["j1"]["clicks"] is None and rows["j1"]["window_label"] == "7d"
    assert rows["j2"]["status"] == "api_error" and rows["j2"]["views"] is None
    assert "secret-token" not in str(history) and "secret-token" not in str(persisted)


def test_collector_resolves_permalink_or_marks_sem_id(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/threads"):
            return httpx.Response(200, json={"data": [
                {"id": "555", "permalink": "https://www.threads.com/@loja/post/ABCD123"}]})
        return httpx.Response(200, json={"data": [{"name": "views", "total_value": {"value": 3}}]})
    jobs = [_job("j1", "user-a", "profile-a", external="https://www.threads.net/@loja/post/ABCD123"),
            _job("j2", "user-a", "profile-a", external="https://www.threads.net/@loja/post/ZZZZ999", post_id=2)]
    persisted, history = _collector(monkeypatch, jobs, handler)
    rows = {row["publish_job_id"]: row for row in history}
    assert rows["j1"]["status"] == "ok" and rows["j1"]["external_id"] == "555"
    assert rows["j1"]["extra"]["resolved_from"] == "permalink"
    assert rows["j2"]["status"] == "sem_id" and rows["j2"]["views"] is None
    assert ("j2", "sem_id", None) in persisted
    assert "/v1.0/555/insights" in calls and not any("ZZZZ" in path for path in calls)


def test_collector_marks_sequence_as_partial(monkeypatch):
    handler = lambda request: httpx.Response(200, json={"data": [{"name": "views", "total_value": {"value": 8}}]})
    persisted, history = _collector(monkeypatch, [_job("j1", "user-a", "profile-a")], handler, multi={1})
    assert history[0]["status"] == "parcial" and history[0]["views"] == 8
    assert history[0]["extra"]["limitation"] == post_insights.SEQUENCE_LIMITATION
    assert persisted[0][1] == "multipart_unmapped"  # leitor legado continua sem somar sequência


def test_two_part_sequence_counts_as_multipart(monkeypatch):
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.in_.return_value = query
    query.execute.return_value = MagicMock(data=[{"id": 2, "post_id": 1}])
    fake = MagicMock()
    fake.table.return_value = query
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    assert post_insights._multi_part_ids("user-a", "p", [{"post_id": 1}]) == {1}


def test_history_failure_never_breaks_collection(monkeypatch):
    broken = MagicMock()
    broken.table.side_effect = RuntimeError("db down")
    monkeypatch.setattr(database_module, "get_supabase", lambda: broken)
    post_insights._record_history({"status": "ok"})  # não levanta


# ---------------- Redirecionador ----------------

TOKEN = "AbCdEfGhIjKlMnOpQrStUv"


@pytest.fixture
def redirect(monkeypatch):
    counted, looked = [], []
    targets = {TOKEN: "https://s.shopee.com.br/abc123", "E" * 22: "https://evil.example.com/x"}

    def count(token):
        counted.append(token)
        return targets.get(token)

    def lookup(token):
        looked.append(token)
        return targets.get(token)
    monkeypatch.setattr(link_redirect, "_count", count)
    monkeypatch.setattr(link_redirect, "_lookup", lookup)
    link_redirect._RATE_STATE.clear()
    app.dependency_overrides.clear()
    yield counted, looked
    link_redirect._RATE_STATE.clear()


def test_redirect_302_to_stored_target_and_counts(redirect):
    counted, _ = redirect
    response = TestClient(app).get(f"/r/{TOKEN}?url=https://evil.example.com", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://s.shopee.com.br/abc123"  # parâmetro ignorado
    assert response.headers["cache-control"] == "no-store" and response.content == b""
    assert counted == [TOKEN]


def test_redirect_unknown_or_malformed_token_is_404(redirect):
    counted, _ = redirect
    client = TestClient(app)
    assert client.get("/r/" + "Z" * 22, follow_redirects=False).status_code == 404
    assert client.get("/r/curto", follow_redirects=False).status_code == 404
    assert counted == ["Z" * 22]


def test_redirect_refuses_non_shopee_target_even_from_db(redirect):
    assert TestClient(app).get("/r/" + "E" * 22, follow_redirects=False).status_code == 404


def test_link_preview_bots_are_redirected_without_counting(redirect):
    counted, looked = redirect
    response = TestClient(app).get(f"/r/{TOKEN}", headers={"User-Agent": "facebookexternalhit/1.1"},
                                   follow_redirects=False)
    assert response.status_code == 302 and counted == [] and looked == [TOKEN]


def test_redirect_rate_limited_per_ip(redirect, monkeypatch):
    monkeypatch.setattr(link_redirect, "RATE_ATTEMPTS", 3)
    client = TestClient(app)
    codes = [client.get(f"/r/{TOKEN}", follow_redirects=False).status_code for _ in range(4)]
    assert codes == [302, 302, 302, 429]
    assert all("." not in str(key) for key in link_redirect._RATE_STATE)  # chave é hash, não IP


def test_redirect_is_not_request_logged(redirect, monkeypatch):
    from api import middleware
    saved = []
    monkeypatch.setattr(middleware.RequestLoggingMiddleware, "_save", lambda *a, **k: saved.append(a))
    TestClient(app).get(f"/r/{TOKEN}", follow_redirects=False)
    assert saved == []

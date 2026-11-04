"""Contratos da visão geral por conta: filtros reais, resumos e falhas."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import dashboard as dashboard_router
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client):
    app.dependency_overrides[get_current_user_id] = lambda: "account-a"
    return client


class ReadOnlyDB:
    """Aplica filtros, projeção, ordem e limite; não oferece escrita."""

    def __init__(self, tables=None, failure=None, missing_count=False, missing_data=False, recent_failure=None):
        self.tables = tables or {}
        self.failure = failure
        self.recent_failure = recent_failure
        self.missing_count = missing_count
        self.missing_data = missing_data
        self.queries = []

    def table(self, name):
        query = ReadOnlyQuery(self, name)
        self.queries.append(query)
        return query


class ReadOnlyQuery:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self.orders = [], []
        self.fields, self.count, self.maximum = "", None, None

    def select(self, fields, count=None):
        self.fields, self.count = fields, count
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def is_(self, column, value):
        assert value == "null"
        self.filters.append((column, None))
        return self

    def order(self, column, desc=False):
        self.orders.append((column, desc))
        return self

    def limit(self, maximum):
        self.maximum = maximum
        return self

    def execute(self):
        if self.db.failure == self.name or (self.count is None and self.db.recent_failure == self.name):
            raise RuntimeError("diagnóstico privado não deve chegar ao cliente")
        rows = [
            row for row in self.db.tables.get(self.name, [])
            if all(row.get(column) == value for column, value in self.filters)
        ]
        total = len(rows)
        for column, descending in reversed(self.orders):
            rows.sort(key=lambda row: row.get(column) or "", reverse=descending)
        rows = rows[:self.maximum]
        data = [{field: row.get(field) for field in self.fields.split(",")} for row in rows]
        return SimpleNamespace(
            count=None if self.db.missing_count else total,
            data=None if self.db.missing_data else data,
        )


def _install(monkeypatch, **kwargs):
    db = ReadOnlyDB(**kwargs)
    monkeypatch.setattr(dashboard_router, "supabase", db)
    return db


def test_requires_auth(client):
    assert client.get("/dashboard/stats").status_code == 401


@pytest.mark.parametrize("active_profile", ["profile-a", "profile-b", None])
def test_aggregates_all_profiles_and_retained_history(auth_client, monkeypatch, active_profile):
    app.dependency_overrides[get_current_profile_id] = lambda: active_profile
    own = [
        {"id": index, "user_id": "account-a", "profile_id": profile,
         "post_id": None, "text": "Resumo", "network": "threads",
         "created_at": f"2026-11-0{index}T10:00:00Z", "activity_id": 1}
        for index, profile in enumerate(["profile-a", "profile-b", None], 1)
    ]
    other = {**own[0], "id": 99, "user_id": "account-b", "text": "privado"}
    child = {**own[0], "id": 98, "post_id": 1}
    db = _install(monkeypatch, tables={
        "products": own + [other], "product_lists": own + [other],
        "schedulers": own + [other], "posts": own + [other, child],
        "activities": own + [other],
    })

    response = auth_client.get("/dashboard/stats")
    assert response.status_code == 200
    result = response.json()
    for field in ("products_count", "posts_count", "lists_count", "scheduled_posts"):
        assert result[field] == 3
    assert [row["id"] for row in result["recent_posts"]] == [3, 2, 1]
    assert [row["id"] for row in result["recent_activities"]] == [3, 2, 1]
    assert "privado" not in response.text
    assert all(("user_id", "account-a") in query.filters for query in db.queries)
    assert all(not any(key == "profile_id" for key, _ in query.filters) for query in db.queries)


def test_recent_projection_limit_order_and_preview(auth_client, monkeypatch):
    rows = [
        {"id": index, "user_id": "account-a", "post_id": None,
         "text": "  Oferta\n" + "x" * 300, "network": "threads",
         "activity_id": index, "created_at": f"2026-11-{index:02d}T10:00:00Z",
         "metadata": {"token": "não expor"}, "profile_id": "não expor"}
        for index in range(1, 9)
    ]
    db = _install(monkeypatch, tables={"posts": rows, "activities": rows})
    response = auth_client.get("/dashboard/stats")
    assert response.status_code == 200
    result = response.json()
    assert [row["id"] for row in result["recent_posts"]] == [8, 7, 6, 5, 4]
    assert len(result["recent_activities"]) == 5
    assert len(result["recent_posts"][0]["text_preview"]) == 160
    assert "\n" not in result["recent_posts"][0]["text_preview"]
    assert set(result["recent_posts"][0]) == {"id", "text_preview", "network", "created_at"}
    assert set(result["recent_activities"][0]) == {"id", "label", "created_at"}
    assert "não expor" not in response.text
    recent = [query for query in db.queries if query.count is None]
    assert [query.fields for query in recent] == [
        "id,text,network,created_at", "id,activity_id,created_at",
    ]
    assert all(query.maximum == 5 for query in recent)
    assert all(query.orders == [("created_at", True), ("id", True)] for query in recent)


def test_activity_labels_do_not_depend_on_activity_types_rows(auth_client, monkeypatch):
    rows = [
        {"id": kind, "user_id": "account-a", "activity_id": kind, "created_at": None}
        for kind in [1, 2, 10, 999]
    ]
    db = _install(monkeypatch, tables={"activities": rows})
    result = auth_client.get("/dashboard/stats").json()
    labels = {row["id"]: row["label"] for row in result["recent_activities"]}
    assert labels == {
        1: "Publicação concluída", 2: "Falha na publicação",
        10: "Informação do agendamento", 999: "Atividade registrada",
    }
    assert not any(query.name == "activity_types" for query in db.queries)


def test_empty_account_is_confirmed_empty(auth_client, monkeypatch):
    _install(monkeypatch)
    response = auth_client.get("/dashboard/stats")
    assert response.status_code == 200
    assert response.json() == {
        "products_count": 0, "posts_count": 0, "lists_count": 0,
        "scheduled_posts": 0, "recent_posts": [], "recent_activities": [],
    }


@pytest.mark.parametrize("table", ["products", "posts", "product_lists", "schedulers"])
def test_query_failure_is_explicit_and_sanitized(auth_client, monkeypatch, table):
    _install(monkeypatch, failure=table)
    response = auth_client.get("/dashboard/stats")
    assert response.status_code == 503
    assert response.json() == {"detail": "Não foi possível carregar a visão geral da conta."}


def test_missing_count_is_not_presented_as_zero(auth_client, monkeypatch):
    _install(monkeypatch, missing_count=True)
    assert auth_client.get("/dashboard/stats").status_code == 503


def test_missing_recent_data_is_explicitly_unavailable(auth_client, monkeypatch):
    _install(monkeypatch, missing_data=True)
    response = auth_client.get("/dashboard/stats")
    assert response.status_code == 200
    assert response.json()["products_count"] == 0
    assert response.json()["recent_posts"] is None
    assert response.json()["recent_activities"] is None


@pytest.mark.parametrize("table,panel,other", [
    ("posts", "recent_posts", "recent_activities"),
    ("activities", "recent_activities", "recent_posts"),
])
def test_recent_failure_preserves_cards_and_other_panel(auth_client, monkeypatch, table, panel, other):
    _install(monkeypatch, recent_failure=table)
    response = auth_client.get("/dashboard/stats")
    assert response.status_code == 200
    result = response.json()
    assert all(result[key] == 0 for key in (
        "products_count", "posts_count", "lists_count", "scheduled_posts",
    ))
    assert result[panel] is None
    assert result[other] == []
    assert "diagnóstico" not in response.text


@pytest.mark.parametrize("stored,expected", [
    ("2026-11-04T12:30:00", "2026-11-04T12:30:00Z"),
    ("2026-11-04T12:30:00.123456", "2026-11-04T12:30:00.123456Z"),
    ("2026-11-04 12:30:00", "2026-11-04T12:30:00Z"),
    ("2026-11-04T12:30:00Z", "2026-11-04T12:30:00Z"),
    ("2026-11-04T12:30:00+00:00", "2026-11-04T12:30:00+00:00"),
    ("2026-11-04T09:30:00-03:00", "2026-11-04T09:30:00-03:00"),
    (None, None),
])
def test_recent_timestamps_have_explicit_utc_without_rewriting_offsets(
    auth_client, monkeypatch, stored, expected,
):
    row = {
        "id": 1, "user_id": "account-a", "post_id": None, "activity_id": 1,
        "text": "Oferta", "network": "threads", "created_at": stored,
    }
    _install(monkeypatch, tables={"posts": [row], "activities": [row]})
    response = auth_client.get("/dashboard/stats")
    assert response.status_code == 200
    assert response.json()["recent_posts"][0]["created_at"] == expected
    assert response.json()["recent_activities"][0]["created_at"] == expected


def test_archived_dispatch_is_not_counted_but_other_history_remains(auth_client, monkeypatch):
    monkeypatch.setenv("PROFILE_ARCHIVAL_ENABLED", "true")
    own = [
        {"id": 1, "user_id": "account-a", "dispatch_cancelled_at": None,
         "post_id": None, "text": "Concluído", "network": "threads",
         "activity_id": 1, "created_at": "2026-11-04T12:00:00Z"},
        {"id": 2, "user_id": "account-a", "dispatch_cancelled_at": "2026-11-04T12:00:00Z",
         "post_id": None, "text": "Arquivado", "network": "threads",
         "activity_id": 2, "created_at": "2026-11-04T13:00:00Z"},
    ]
    _install(monkeypatch, tables={
        "schedulers": own, "posts": own, "activities": own,
        "products": own, "product_lists": own,
    })
    data = auth_client.get("/dashboard/stats").json()
    assert data["scheduled_posts"] == 1
    assert data["posts_count"] == 2
    assert len(data["recent_posts"]) == 2
    assert len(data["recent_activities"]) == 2

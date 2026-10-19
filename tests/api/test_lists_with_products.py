"""Listas com produtos: PUT/POST com product_ids contra um fake Supabase estrito.

O fake reproduz a limitação real do postgrest-py: `.single()` só existe em
builders de SELECT (update/insert/delete não têm). Os mocks do test_lists.py
(MagicMock) aceitam qualquer método e por isso escondiam o 500 em produção."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import lists as lists_router
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id

USER = 42


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.op, self.payload, self.filters = "select", None, []

    def select(self, *_a):
        self.op = "select"
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append((col, [val]))
        return self

    def in_(self, col, vals):
        self.filters.append((col, list(vals)))
        return self

    def single(self):
        if self.op != "select":  # postgrest-py: só builders de SELECT têm .single()
            raise AttributeError("'SyncFilterRequestBuilder' object has no attribute 'single'")
        self._single = True
        return self

    def maybe_single(self):
        return self.single()

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def _match(self, row):
        return all(row.get(c) in vals for c, vals in self.filters)

    def execute(self):
        rows = self.db.tables[self.name]
        if self.op == "insert":
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for item in new:
                item = dict(item)
                if self.name == "product_lists":
                    self.db.seq += 1
                    item.setdefault("id", self.db.seq)
                    item.setdefault("created_at", "2026-01-01T00:00:00")
                if self.db.fail_insert_on == self.name:
                    raise RuntimeError("boom")
                rows.append(item)
                out.append(item)
            return _Result(out)
        hit = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hit:
                r.update(self.payload)
            return _Result([dict(r) for r in hit])
        if self.op == "delete":
            for r in hit:
                rows.remove(r)
            return _Result([dict(r) for r in hit])
        if getattr(self, "_single", False):
            return _Result(dict(hit[0]) if hit else None)
        return _Result([dict(r) for r in hit])


class FakeSupabase:
    def __init__(self):
        self.seq = 100
        self.fail_insert_on = None
        self.tables = {
            "product_lists": [{"id": 1, "name": "Antiga", "user_id": USER, "profile_id": "profile-a", "created_at": "x"}],
            "product_lists_products": [],
            "products": [
                {"id": 10, "user_id": USER},
                {"id": 20, "user_id": USER},
                {"id": 99, "user_id": 7},  # de outro usuário
            ],
        }

    def table(self, name):
        return _Query(self, name)


@pytest.fixture
def fake(monkeypatch):
    db = FakeSupabase()
    monkeypatch.setattr(lists_router, "supabase", db)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: USER
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield db
    app.dependency_overrides.clear()


def _assoc(db):
    return sorted((r["product_list_id"], r["product_id"]) for r in db.tables["product_lists_products"])


def test_put_with_products_does_not_500(fake):
    res = TestClient(app).put("/lists/1", json={"name": "Nova", "product_ids": [10, 20]})
    assert res.status_code == 200
    assert res.json()["name"] == "Nova"
    assert _assoc(fake) == [(1, 10), (1, 20)]


def test_put_with_foreign_product_is_4xx_and_changes_nothing(fake):
    res = TestClient(app).put("/lists/1", json={"name": "Nova", "product_ids": [10, 99]})
    assert res.status_code == 400
    assert "99" in res.json()["detail"]
    assert _assoc(fake) == []


def test_post_with_products_creates_list_and_associations(fake):
    res = TestClient(app).post("/lists", json={"name": "Com produtos", "product_ids": [10, 20]})
    assert res.status_code == 200
    body = res.json()
    assert body["product_count"] == 2
    assert _assoc(fake) == [(body["id"], 10), (body["id"], 20)]


def test_post_without_products_still_works(fake):
    res = TestClient(app).post("/lists", json={"name": "Vazia"})
    assert res.status_code == 200
    assert res.json()["product_count"] == 0


def test_post_with_foreign_product_creates_nothing(fake):
    res = TestClient(app).post("/lists", json={"name": "X", "product_ids": [99]})
    assert res.status_code == 400
    assert [r["name"] for r in fake.tables["product_lists"]] == ["Antiga"]


def test_post_rolls_back_list_when_association_fails(fake):
    fake.fail_insert_on = "product_lists_products"
    res = TestClient(app, raise_server_exceptions=False).post(
        "/lists", json={"name": "X", "product_ids": [10]}
    )
    assert res.status_code >= 400
    assert [r["name"] for r in fake.tables["product_lists"]] == ["Antiga"]

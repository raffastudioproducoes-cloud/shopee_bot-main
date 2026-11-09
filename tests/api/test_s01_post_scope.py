"""S-01: helpers de thread exigem o dono; ID de outra conta responde 404 e não altera nada."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.routers import posts as posts_module

A, B = 1, 2


class _Query:
    def __init__(self, db, table):
        self.db, self.table_name = db, table
        self.filters, self.nulls, self.mode = [], [], None
        self.deleting = False

    def select(self, *_a, **_k):
        return self

    def delete(self):
        self.deleting = True
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def is_(self, col, _val):
        self.nulls.append(col)
        return self

    def single(self):
        self.mode = "single"
        return self

    def maybe_single(self):
        self.mode = "maybe"
        return self

    def _rows(self):
        rows = self.db.tables.get(self.table_name, [])
        for col, val in self.filters:
            rows = [r for r in rows if r.get(col) == val]
        for col in self.nulls:
            rows = [r for r in rows if r.get(col) is None]
        return rows

    def execute(self):
        rows = self._rows()
        if self.deleting:
            self.db.deleted.append((self.table_name, list(self.filters)))
            return SimpleNamespace(data=[])
        if self.mode in ("single", "maybe"):
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


class _DB:
    def __init__(self):
        self.deleted = []
        self.tables = {
            "posts": [
                {"id": 10, "user_id": A, "post_id": None, "profile_id": "pa", "text": "head A"},
                {"id": 11, "user_id": A, "post_id": 10, "profile_id": "pa", "text": "parte 2 A"},
                {"id": 20, "user_id": B, "post_id": None, "profile_id": "pb", "text": "head B"},
            ],
            "posts_medias": [],
        }

    def table(self, name):
        return _Query(self, name)


@pytest.fixture
def db(monkeypatch):
    fake = _DB()
    monkeypatch.setattr(posts_module, "supabase", fake)
    return fake


def test_owner_reads_own_thread_chain(db):
    chain = posts_module._get_thread_chain(10, A)
    assert [row["id"] for row in chain] == [10, 11]


@pytest.mark.parametrize("head_id", [10, 11])
def test_other_account_cannot_read_thread_chain(db, head_id):
    with pytest.raises(HTTPException) as err:
        posts_module._get_thread_chain(head_id, B)
    assert err.value.status_code == 404


def test_other_account_cannot_fetch_post_by_id(db):
    with pytest.raises(HTTPException) as err:
        posts_module._get_post_by_id_only(10, B)
    assert err.value.status_code == 404


def test_other_account_cannot_delete_thread_cascade_and_nothing_is_deleted(db):
    with pytest.raises(HTTPException) as err:
        posts_module._delete_thread_cascade(10, B)
    assert err.value.status_code == 404
    assert db.deleted == []


def test_helpers_require_user_id_argument():
    import inspect

    for fn in (posts_module._get_thread_chain, posts_module._get_post_by_id_only, posts_module._delete_thread_cascade):
        params = inspect.signature(fn).parameters
        assert "user_id" in params and params["user_id"].default is inspect.Parameter.empty, fn.__name__

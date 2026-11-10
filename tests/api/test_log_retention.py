"""Retenção de 90 dias de request_logs: só apaga o que passou do prazo, em blocos, sem propagar erro."""
from datetime import datetime, timedelta, timezone

from api import log_retention

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


class _Result:
    def __init__(self, data=None):
        self.data = data


class _Query:
    def __init__(self, db):
        self.db, self.op, self.cutoff, self.ids, self.max = db, None, None, None, None

    def select(self, *_):
        self.op = "select"; return self

    def delete(self):
        self.op = "delete"; return self

    def lt(self, column, value):
        assert column == "created_at"; self.cutoff = value; return self

    def in_(self, column, ids):
        assert column == "id"; self.ids = ids; return self

    def order(self, *_):
        return self

    def limit(self, n):
        self.max = n; return self

    def execute(self):
        if self.op == "select":
            old = [r["id"] for r in self.db.rows if r["created_at"] < self.cutoff]
            return _Result([{"id": i} for i in old[: self.max]])
        self.db.deleted.append(list(self.ids))
        self.db.rows = [r for r in self.db.rows if r["id"] not in self.ids]
        return _Result([])


class _FakeSupabase:
    def __init__(self, rows):
        self.rows, self.deleted = rows, []

    def table(self, name):
        assert name == "request_logs"          # nenhuma outra tabela é tocada
        return _Query(self)


def _row(i, days_old):
    return {"id": i, "created_at": (NOW - timedelta(days=days_old)).isoformat()}


def test_cutoff_is_ninety_days():
    assert log_retention.retention_cutoff(NOW) == NOW - timedelta(days=90)


def test_only_rows_older_than_ninety_days_are_removed(monkeypatch):
    fake = _FakeSupabase([_row(1, 200), _row(2, 91), _row(3, 89), _row(4, 1)])
    monkeypatch.setattr(log_retention, "supabase", fake)
    assert log_retention.purge_old_request_logs(NOW) == 2
    assert sorted(r["id"] for r in fake.rows) == [3, 4]


def test_large_backlog_is_deleted_in_batches(monkeypatch):
    fake = _FakeSupabase([_row(i, 120) for i in range(1, 1202)])
    monkeypatch.setattr(log_retention, "supabase", fake)
    assert log_retention.purge_old_request_logs(NOW) == 1201
    assert [len(batch) for batch in fake.deleted] == [500, 500, 201]


def test_nothing_to_delete_makes_no_delete_call(monkeypatch):
    fake = _FakeSupabase([_row(1, 5)])
    monkeypatch.setattr(log_retention, "supabase", fake)
    assert log_retention.purge_old_request_logs(NOW) == 0
    assert fake.deleted == []


def test_scheduler_entry_never_raises(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("banco fora")
    monkeypatch.setattr(log_retention, "purge_old_request_logs", boom)
    assert log_retention.run_log_retention() == 0

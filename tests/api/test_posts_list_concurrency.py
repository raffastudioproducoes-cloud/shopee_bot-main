"""A listagem de posts não pode enriquecer os posts um a um.

Cada post faz ~9 consultas ao banco. Em série, 90 posts passavam de 800 idas ao banco e a
página de Posts estourava o tempo do proxy (30 s). O teste usa uma barreira: se a listagem
processar em série, a barreira nunca fecha e o teste falha por tempo.
"""
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


class _Heads:
    def __init__(self, rows):
        self.rows = rows

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class _DB:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _name):
        return _Heads(self.rows)


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 1
    app.dependency_overrides[get_current_profile_id] = lambda: "p1"
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_posts_are_enriched_concurrently(monkeypatch, client):
    rows = [{"id": i, "created_at": f"2026-11-09T12:00:{i:02d}+00:00"} for i in range(8)]
    monkeypatch.setattr(posts_module, "supabase", _DB(rows))
    monkeypatch.setattr(posts_module, "_post_admin_access", lambda _u: False)
    barrier = threading.Barrier(4, timeout=5)
    peak = {"now": 0, "max": 0}
    lock = threading.Lock()

    def fake_enrich(item, _user, _profile, _admin):
        with lock:
            peak["now"] += 1
            peak["max"] = max(peak["max"], peak["now"])
        try:
            barrier.wait()  # só passa se 4 posts estiverem sendo tratados ao mesmo tempo
        except threading.BrokenBarrierError:
            pass
        finally:
            with lock:
                peak["now"] -= 1
        return {**item, "texts": ["x"]}

    monkeypatch.setattr(posts_module, "_enrich_listed_post", fake_enrich)
    res = client.get("/posts?limit=8")
    assert res.status_code == 200
    assert [p["id"] for p in res.json()["data"]] == list(range(8))  # ordem preservada
    assert peak["max"] >= 4


def test_concurrency_is_bounded(monkeypatch, client):
    rows = [{"id": i, "created_at": "2026-11-09T12:00:00+00:00"} for i in range(40)]
    monkeypatch.setattr(posts_module, "supabase", _DB(rows))
    monkeypatch.setattr(posts_module, "_post_admin_access", lambda _u: False)
    seen = {"now": 0, "max": 0}
    lock = threading.Lock()

    def fake_enrich(item, *_):
        with lock:
            seen["now"] += 1
            seen["max"] = max(seen["max"], seen["now"])
        threading.Event().wait(0.01)
        with lock:
            seen["now"] -= 1
        return {**item}

    monkeypatch.setattr(posts_module, "_enrich_listed_post", fake_enrich)
    assert client.get("/posts?limit=40").status_code == 200
    assert seen["max"] <= posts_module._LIST_ENRICH_CONCURRENCY

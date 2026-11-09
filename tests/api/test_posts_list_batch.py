"""A listagem de posts busca tudo em lote e devolve o MESMO resultado da versão individual.

Antes, cada post fazia ~9 consultas ao banco em série (90 posts = 800+ consultas, >30 s e erro de
tempo esgotado na página). Agora o número de consultas não cresce com a quantidade de posts.
"""
import copy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id

USER, PROFILE = 7, "p-1"


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.f, self.orders, self.max, self.one = db, table, [], [], None, None

    def select(self, *_a, **_k):
        return self

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **k: self

    def eq(self, col, val):
        self.f.append(("eq", col, str(val)))
        return self

    def in_(self, col, vals):
        self.f.append(("in", col, {str(v) for v in vals}))
        return self

    def is_(self, col, _v):
        self.f.append(("null", col, None))
        return self

    def order(self, col, desc=False):
        self.orders.append((col, desc))
        return self

    def limit(self, n):
        self.max = n
        return self

    def maybe_single(self):
        self.one = "maybe"
        return self

    single = maybe_single

    def execute(self):
        self.db.calls += 1
        rows = [r for r in self.db.tables.get(self.table, []) if self._match(r)]
        for col, desc in reversed(self.orders):
            rows.sort(key=lambda r: (r.get(col) is None, r.get(col) or ""), reverse=desc)
        if self.max is not None:
            rows = rows[: self.max]
        rows = copy.deepcopy(rows)
        if self.one:
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)

    def _match(self, row):
        for kind, col, val in self.f:
            cur = row.get(col)
            if kind == "eq" and str(cur) != val:
                return False
            if kind == "in" and str(cur) not in val:
                return False
            if kind == "null" and cur is not None:
                return False
        return True


class _DB:
    def __init__(self, tables):
        self.tables, self.calls = tables, 0

    def table(self, name):
        return _Q(self, name)


def _seed(n_posts: int) -> dict:
    t: dict[str, list] = {k: [] for k in ("posts", "schedulers", "posts_products", "posts_medias", "publish_jobs", "activities")}
    next_id = 1000
    for i in range(1, n_posts + 1):
        base = f"2026-11-0{1 + i % 9}T10:00:00"
        t["posts"].append({"id": i, "user_id": USER, "profile_id": PROFILE, "post_id": None, "text": f"cabeça {i}",
                           "created_at": base, "publish_immediately": i % 7 == 0})
        if i % 3 == 0:  # thread de 3 partes
            for part in (1, 2):
                next_id += 1
                prev = i if part == 1 else next_id - 1
                t["posts"].append({"id": next_id, "user_id": USER, "profile_id": PROFILE, "post_id": prev,
                                   "text": f"parte {part} de {i}", "created_at": base})
        t["schedulers"].append({"id": f"s{i}", "user_id": USER, "post_id": i, "trigger": "date" if i % 2 else "cron",
                                "run_date": f"2026-12-0{1 + i % 9}", "time": "09:00", "day_of_week": None,
                                "days_of_week": None, "start_date": None})
        if i % 4 == 0:
            t["schedulers"].append({"id": f"s{i}b", "user_id": USER, "post_id": i, "trigger": "cron", "run_date": None,
                                    "time": "18:00", "day_of_week": "mon", "days_of_week": None, "start_date": None})
        for order in (1, 2):
            t["posts_products"].append({"post_id": i, "display_order": order,
                                        "products": {"id": i * 10 + order, "product_id": str(i * 10 + order), "name": f"p{order}",
                                                     "image": None, "price_min": "1", "price_max": "2", "commission": "3"}})
        if i % 5 == 0:
            t["posts_medias"].append({"post_id": i, "display_order": 0,
                                      "medias": {"id": i, "file_name": "a.jpg", "size": 10, "type": "image"}})
        scenario = i % 6
        meta = {"post_id": str(i), "key": "m"}
        if scenario == 0:  # sucesso na fila
            t["publish_jobs"].append(_job(i, "succeeded", "2026-11-08T10:00:00", "2026-11-08T10:01:00"))
        elif scenario == 1:  # falha na fila + evento de falha mais novo
            t["publish_jobs"].append(_job(i, "failed", "2026-11-08T10:00:00", "2026-11-08T10:01:00", err="boom"))
            t["activities"].append(_act(i, 2, "2026-11-08T10:02:00", {"error": "falhou"}))
        elif scenario == 2:  # evento de publicado mais novo que o job
            t["publish_jobs"].append(_job(i, "succeeded", "2026-11-07T10:00:00", "2026-11-07T10:01:00"))
            t["activities"].append(_act(i, 1, "2026-11-08T11:00:00", meta))
        elif scenario == 3:  # unknown com erro legado 4xx (falha parcial)
            t["publish_jobs"].append(_job(i, "unknown", "2026-11-08T10:00:00", "2026-11-08T10:00:30", sched=f"s{i}"))
            t["activities"].append(_act(i, 2, "2026-11-08T10:00:40", {
                "published_parts": 1, "job_id": f"s{i}", "error": "Failed to Create Media Container HTTP 400"}))
        elif scenario == 4:  # retry manual pendente
            t["publish_jobs"].append(_job(i, "pending", "2026-11-08T10:00:00", None, key="manual_retry:abc"))
        # scenario 5: sem fila nem evento
        if i % 8 == 0:  # histórico longo: vários jobs/eventos antigos
            for d in range(1, 4):
                t["publish_jobs"].append(_job(i, "succeeded", f"2026-10-0{d}T10:00:00", f"2026-10-0{d}T10:01:00"))
                t["activities"].append(_act(i, 1, f"2026-10-0{d}T10:02:00", {"post_id": str(i)}))
    # dados de OUTRA conta/perfil nunca podem aparecer
    t["publish_jobs"].append({**_job(1, "succeeded", "2026-11-09T10:00:00", "2026-11-09T10:01:00"), "user_id": 99})
    t["activities"].append({**_act(1, 1, "2026-11-09T10:00:00", {"post_id": "1"}), "user_id": 99})
    return t


def _job(post_id, status, created, finished, err=None, key=None, sched=None):
    return {"id": f"j{post_id}-{status}-{created}", "post_id": post_id, "user_id": USER, "profile_id": PROFILE,
            "scheduler_id": sched, "status": status, "idempotency_key": key, "created_at": created,
            "started_at": created, "finished_at": finished, "last_error": err, "external_id": None}


def _act(post_id, activity_id, created, metadata):
    meta = {"post_id": str(post_id), **metadata}
    return {"user_id": USER, "profile_id": PROFILE, "activity_id": activity_id, "created_at": created,
            "metadata": meta, "metadata->>post_id": str(post_id)}


@pytest.mark.parametrize("is_admin", [False, True])
def test_batch_result_equals_individual_result(monkeypatch, is_admin):
    db = _DB(_seed(24))
    monkeypatch.setattr(posts_module, "supabase", db)
    heads = [r for r in db.tables["posts"] if r["post_id"] is None]
    expected = [posts_module._enrich_listed_post(copy.deepcopy(h), USER, PROFILE, is_admin) for h in heads]
    actual = posts_module._enrich_listed_posts(copy.deepcopy(heads), USER, PROFILE, is_admin)
    assert actual == expected
    assert any(p["parts_count"] == 3 for p in actual)          # threads montadas
    assert any(p["last_result"] and p["last_result"].get("partial_failure") for p in actual)
    assert any(p["last_published_at"] for p in actual)


def test_number_of_queries_does_not_grow_with_posts(monkeypatch):
    counts = {}
    for n in (6, 60):
        db = _DB(_seed(n))
        monkeypatch.setattr(posts_module, "supabase", db)
        heads = [r for r in db.tables["posts"] if r["post_id"] is None]
        posts_module._enrich_listed_posts(heads, USER, PROFILE, False)
        counts[n] = db.calls
    assert counts[60] <= 4 * counts[6], counts       # 60 posts = 4 blocos de 15; não 60x
    assert counts[60] < 60, counts                   # antes: ~9 consultas POR post


def test_list_endpoint_returns_batched_posts(monkeypatch):
    db = _DB(_seed(10))
    monkeypatch.setattr(posts_module, "supabase", db)
    monkeypatch.setattr(posts_module, "_post_admin_access", lambda _u: False)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: USER
    app.dependency_overrides[get_current_profile_id] = lambda: PROFILE
    try:
        res = TestClient(app, raise_server_exceptions=False).get("/posts?limit=10")
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 200
    body = res.json()
    assert len(body["data"]) == 10 and body["data"][0]["texts"]

"""A ordem das mídias lida do banco deve seguir posts_medias.display_order.

Sem Postgres efêmero: captura o SQL enviado e confere o contrato. O bug
original era `array_agg(DISTINCT jsonb_build_object(...))`, que ordena por
valor do jsonb (e não pela ordem escolhida pelo usuário).
"""
import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

POSTS_PATH = Path(__file__).resolve().parents[2] / "database" / "posts.py"


@pytest.fixture
def posts(monkeypatch):
    """Carrega database/posts.py sem inicializar o pool/migrações do Postgres."""
    stub = types.ModuleType("shopee_bot.database")
    stub.query_db = stub.execute_db = lambda *a, **k: []
    pkg = types.ModuleType("shopee_bot")
    pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "shopee_bot", pkg)
    monkeypatch.setitem(sys.modules, "shopee_bot.database", stub)
    spec = importlib.util.spec_from_file_location("_posts_under_test", POSTS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture(monkeypatch, posts, fn, *args):
    seen = {}

    def fake_query_db(query, args=None, one=False):
        seen["sql"] = query
        return []

    monkeypatch.setattr(posts, "query_db", fake_query_db)
    fn(*args)
    return re.sub(r"\s+", " ", seen["sql"])


def _medias_aggregate(sql):
    start = sql.index("jsonb_build_object") if "jsonb_build_object" in sql else sql.index("json_build_object")
    return sql[max(0, start - 200): start + 700]


def test_get_orders_medias_by_display_order_without_distinct(monkeypatch, posts):
    sql = _capture(monkeypatch, posts, posts.get, 1, 2, "p")
    agg = _medias_aggregate(sql)
    assert "DISTINCT jsonb_build_object" not in sql
    assert re.search(r"ORDER BY \w+\.display_order, \w+\.id", agg)


def test_query_paginated_orders_medias_by_display_order(monkeypatch, posts):
    sql = _capture(monkeypatch, posts, posts.query_paginated, 1, None, 10)
    assert re.search(r"ORDER BY pm\.display_order, m\.id\s*\) FILTER", sql)

"""Contratos SQL de isolamento por usuário/perfil, sem publicar nem acessar rede."""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

POSTS_PATH = Path(__file__).resolve().parents[2] / "database" / "posts.py"


@pytest.fixture
def posts_module(monkeypatch):
    stub = types.ModuleType("shopee_bot.database")
    stub.query_db = stub.execute_db = lambda *a, **k: []
    pkg = types.ModuleType("shopee_bot")
    pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "shopee_bot", pkg)
    monkeypatch.setitem(sys.modules, "shopee_bot.database", stub)
    spec = importlib.util.spec_from_file_location("_posts_identity_test", POSTS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture(monkeypatch, module, call):
    seen = {}

    def fake_query(sql, args, one=False):
        seen.update(sql=" ".join(sql.lower().split()), args=args)
        return []

    monkeypatch.setattr(module, "query_db", fake_query)
    call()
    return seen


def test_thread_read_requires_owner_and_profile_at_every_depth(monkeypatch, posts_module):
    seen = _capture(
        monkeypatch, posts_module,
        lambda: posts_module.get("user-a", 17, "00000000-0000-0000-0000-000000000001"),
    )
    assert "where id = %s and user_id = %s and profile_id = %s::uuid" in seen["sql"]
    assert "where p.user_id = %s and p.profile_id = %s::uuid" in seen["sql"]
    assert "s.user_id = ph.user_id" in seen["sql"]
    assert "s.profile_id is not distinct from ph.profile_id" in seen["sql"]
    assert seen["args"] == (
        17, "user-a", "00000000-0000-0000-0000-000000000001",
        "user-a", "00000000-0000-0000-0000-000000000001",
    )


def test_thread_delete_never_walks_another_users_children(monkeypatch, posts_module):
    seen = _capture(
        monkeypatch, posts_module,
        lambda: posts_module.get_for_delete("user-a", 17),
    )
    assert "where id = %s and user_id = %s" in seen["sql"]
    assert "where p.user_id = %s and p.profile_id is not distinct from ph.profile_id" in seen["sql"]
    assert seen["args"] == (17, "user-a", "user-a")


def test_listing_recursion_is_tenant_scoped(monkeypatch, posts_module):
    seen = _capture(
        monkeypatch, posts_module,
        lambda: posts_module.query_paginated("user-a", None, 20),
    )
    assert "where post_id is null and user_id = %s" in seen["sql"]
    assert "where p.user_id = %s" in seen["sql"]
    assert "s.profile_id is not distinct from p.profile_id" in seen["sql"]
    assert seen["args"] == ["user-a", "user-a", None, None, None, None, "user-a", 20]


def test_edit_targets_existing_post_id_not_a_new_insert(monkeypatch, posts_module):
    seen = {}

    def fake_exec(sql, args, conn=None):
        seen.update(sql=" ".join(sql.lower().split()), args=args)
        return 17

    monkeypatch.setattr(posts_module, "execute_db", fake_exec)
    assert posts_module.update("user-a", 17, {"text": "texto atualizado"}) == 17
    assert "update posts set" in seen["sql"]
    assert "where id = %s and user_id = %s" in seen["sql"]
    assert seen["args"][-2:] == (17, "user-a")

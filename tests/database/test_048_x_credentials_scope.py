"""Contrato estático da migration 048 e do SQL que lê/grava o escopo do X."""
import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_048_is_additive_and_idempotent():
    sql = (ROOT / "database/migrations/048_add_x_credentials_scope.sql").read_text(encoding="utf-8").lower()
    assert "add column if not exists scope text" in sql
    assert "alter table x_credentials" in sql
    for forbidden in ("drop ", "delete ", "update ", "truncate"):
        assert forbidden not in sql


@pytest.fixture
def xc(monkeypatch):
    seen = []
    stub = types.ModuleType("shopee_bot.database")
    stub.query_db = lambda q, a=None, one=False: seen.append((q, a)) or {}
    stub.execute_db = lambda q, a=None, conn=None: seen.append((q, a))
    crypto = types.ModuleType("shopee_bot.utils.crypto")
    crypto.encrypt = lambda v: f"enc({v})" if v else v
    crypto.decrypt = lambda v: v
    for name, mod in (("shopee_bot", types.ModuleType("shopee_bot")), ("shopee_bot.database", stub),
                      ("shopee_bot.utils", types.ModuleType("shopee_bot.utils")), ("shopee_bot.utils.crypto", crypto)):
        if name in ("shopee_bot", "shopee_bot.utils"):
            mod.__path__ = []
        monkeypatch.setitem(sys.modules, name, mod)
    spec = importlib.util.spec_from_file_location("_xc_under_test", ROOT / "database/x_credentials.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, seen


def test_get_by_user_id_selects_scope(xc):
    module, seen = xc
    module.get_by_user_id(1, "p")
    assert "xc.scope x_scope" in seen[0][0]


def test_update_tokens_keeps_scope_when_refresh_omits_it(xc):
    module, seen = xc
    module.update_tokens(1, "p", {"access_token": "a", "refresh_token": "r"})
    sql, args = seen[0]
    assert "scope = COALESCE(%s, scope)" in re.sub(r"\s+", " ", sql)
    assert args[-3] is None
    module.update_tokens(1, "p", {"access_token": "a", "scope": "media.write"})
    assert seen[1][1][-3] == "media.write"

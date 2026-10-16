"""F-02: todo UPDATE/DELETE de credenciais/OAuth carrega filtro de dono."""

from api.routers import credentials, meta_callbacks


class _RecTable:
    def __init__(self, inner, log):
        self._inner, self._log, self._ops = inner, log, []

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            result = attr(*args, **kwargs)
            self._ops.append((name, args))
            if name == "execute":
                self._log.append(list(self._ops))
                return result
            return self if result is self._inner else result

        return call


class _RecDB:
    def __init__(self, db):
        self._db, self.log = db, []

    def table(self, name):
        return _RecTable(self._db.table(name), self.log)


def _writes(rec, table_ops=("update", "delete")):
    return [ops for ops in rec.log if ops[0][0] in table_ops]


def _filters(ops):
    return {args[0] for name, args in ops if name in ("eq", "is_")}


def test_meta_callback_update_ignores_row_now_owned_by_someone_else(fake_db, monkeypatch):
    db = fake_db({"instagram_credentials": [
        {"id": 1, "user_id": "user-b", "profile_id": "profile-b", "status": True},
    ]})
    monkeypatch.setattr(meta_callbacks, "supabase", db)
    stale = [{"id": 1, "user_id": "user-a", "profile_id": "profile-a"}]

    affected = meta_callbacks._update_credentials("instagram_credentials", stale, {"status": False})

    assert affected == 0
    assert db.tables["instagram_credentials"][0]["status"] is True


def test_meta_callback_update_without_profile_only_matches_null_profile(fake_db, monkeypatch):
    db = fake_db({"threads_credentials": [
        {"id": 1, "user_id": "user-a", "profile_id": "profile-x", "status": True},
        {"id": 2, "user_id": "user-a", "profile_id": None, "status": True},
    ]})
    monkeypatch.setattr(meta_callbacks, "supabase", db)
    rows = [{"id": 1, "user_id": "user-a", "profile_id": None}, {"id": 2, "user_id": "user-a", "profile_id": None}]

    meta_callbacks._update_credentials("threads_credentials", rows, {"status": False})

    assert [r["status"] for r in db.tables["threads_credentials"]] == [True, False]


def test_save_check_update_is_scoped_to_owner(fake_db, monkeypatch):
    base = fake_db({"credential_checks": [
        {"id": 5, "user_id": 1, "profile_id": "p1", "network": "threads", "state": "ok"},
    ]})
    rec = _RecDB(base)
    monkeypatch.setattr(credentials, "supabase", rec)

    credentials._save_check(1, "p1", "threads", "failed", "x")

    writes = _writes(rec, ("update",))
    assert writes and all("user_id" in _filters(ops) for ops in writes)


def test_save_check_account_network_update_is_scoped_to_owner(fake_db, monkeypatch):
    base = fake_db({"credential_checks": [
        {"id": 5, "user_id": 1, "profile_id": None, "network": "shopee", "state": "ok"},
    ]})
    rec = _RecDB(base)
    monkeypatch.setattr(credentials, "supabase", rec)

    credentials._save_check(1, None, "shopee", "failed", "x")

    writes = _writes(rec, ("update",))
    assert writes and all("user_id" in _filters(ops) for ops in writes)

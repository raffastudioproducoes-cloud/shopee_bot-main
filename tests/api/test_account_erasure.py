"""Exclusão integral: etapas retomáveis sem acesso a contas/arquivos reais."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api import account_erasure as svc
from api.routers import users as users_router


def _fake_backend(monkeypatch, *, storage_fail=False, auth_fail=False):
    calls = []
    manifests = [
        [{"bucket_id": "post-media", "object_name": "drafts/owner/path.png"},
         {"bucket_id": "avatars", "object_name": "profile/avatar.jpg"}],
        [],
    ]
    backend = MagicMock()

    def rpc(name, params):
        calls.append(("rpc", name, dict(params)))
        if name == "begin_account_erasure":
            data = {"user_id": params["p_user_id"], "auth_user_id": "auth-uuid"}
        elif name == "account_erasure_storage_manifest":
            data = manifests.pop(0) if manifests else []
        elif name in {"mark_account_erasure_storage_complete", "mark_account_erasure_auth_complete"}:
            data = True
        elif name == "finalize_account_erasure":
            data = {"status": "deleted"}
        else:
            raise AssertionError(name)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))

    backend.rpc.side_effect = rpc

    def remove_factory(bucket):
        def remove(keys):
            calls.append(("storage", bucket, list(keys)))
            if storage_fail:
                raise RuntimeError("private storage error")
        return SimpleNamespace(remove=remove)

    backend.storage.from_.side_effect = remove_factory
    def delete_auth(uid):
        calls.append(("auth", uid))
        if auth_fail:
            raise RuntimeError("private auth error")
    backend.auth.admin.delete_user.side_effect = delete_auth
    monkeypatch.setattr(svc, "supabase", backend)
    monkeypatch.setenv("ACCOUNT_ERASURE_ENABLED", "true")
    return calls


def test_erasure_orders_storage_before_auth_before_database(monkeypatch):
    calls = _fake_backend(monkeypatch)
    assert svc.erase_account("account-uuid") == {"status": "deleted"}
    names = [value[1] for value in calls if value[0] == "rpc"]
    assert names == [
        "begin_account_erasure",
        "account_erasure_storage_manifest",
        "account_erasure_storage_manifest",
        "mark_account_erasure_storage_complete",
        "mark_account_erasure_auth_complete",
        "finalize_account_erasure",
    ]
    storage_positions = [i for i, c in enumerate(calls) if c[0] == "storage"]
    auth_position = next(i for i, c in enumerate(calls) if c[0] == "auth")
    final_position = next(i for i, c in enumerate(calls) if c[:2] == ("rpc", "finalize_account_erasure"))
    assert storage_positions and max(storage_positions) < auth_position < final_position


@pytest.mark.parametrize("failure", ["storage", "auth"])
def test_failed_external_step_never_finalizes_database(monkeypatch, failure):
    calls = _fake_backend(
        monkeypatch, storage_fail=failure == "storage", auth_fail=failure == "auth"
    )
    with pytest.raises(RuntimeError):
        svc.erase_account("account-uuid")
    assert not any(c[:2] == ("rpc", "finalize_account_erasure") for c in calls)


def test_disabled_erasure_does_nothing(monkeypatch):
    monkeypatch.setenv("ACCOUNT_ERASURE_ENABLED", "false")
    stub = MagicMock()
    monkeypatch.setattr(svc, "supabase", stub)
    with pytest.raises(RuntimeError, match="disabled"):
        svc.erase_account("account-uuid")
    stub.rpc.assert_not_called()


def test_user_helper_never_falls_back_to_physical_delete(monkeypatch):
    monkeypatch.setattr(users_router, "account_erasure_enabled", lambda: True)
    stub = MagicMock(side_effect=RuntimeError("storage error private"))
    monkeypatch.setattr(users_router, "erase_account", stub)
    with pytest.raises(HTTPException) as raised:
        users_router._delete_user_row("account-uuid")
    assert raised.value.status_code == 503
    assert "storage error private" not in raised.value.detail
    stub.assert_called_once_with("account-uuid")


def test_legacy_password_requires_valid_hash(monkeypatch):
    monkeypatch.setattr(users_router.pwd_context, "verify", lambda pwd, old: pwd == "certa")
    with pytest.raises(HTTPException) as raised:
        users_router._verify_self_delete_password(
            {"supabase_auth_user_id": None, "password": "hash"}, "errada"
        )
    assert raised.value.status_code == 403


def test_auth_linked_account_must_match_supabase_identity(monkeypatch):
    monkeypatch.setattr(users_router.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(users_router.settings, "supabase_auth_publishable_key", "test-public")
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="other-auth-id")
    )
    monkeypatch.setattr(users_router, "create_client", lambda *args: client)
    with pytest.raises(HTTPException) as raised:
        users_router._verify_self_delete_password({
            "supabase_auth_user_id": "expected-auth-id",
            "email": "synthetic@example.invalid",
            "password": None,
        }, "senha")
    assert raised.value.status_code == 403

"""Storage Free: reserva global, falha fechada e agregados do ADMIN."""
import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api import storage_capacity
from api import admin_metrics


class FakeSupabase:
    def __init__(self, decisions):
        self.decisions = decisions
        self.calls = []
        self.release_fails = False

    def rpc(self, name, params=None):
        self.calls.append((name, params))
        parent = self

        class Result:
            def execute(self):
                if name == "reserve_storage_upload":
                    if isinstance(parent.decisions, Exception):
                        raise parent.decisions
                    return SimpleNamespace(data=parent.decisions)
                if name == "release_storage_upload" and parent.release_fails:
                    raise RuntimeError("offline")
                return SimpleNamespace(data=None)
        return Result()


def test_global_reservation_guards_upload_and_releases(monkeypatch):
    fake = FakeSupabase({"allowed": True, "reservation_id": "22222222-2222-4222-8222-222222222222"})
    monkeypatch.setattr(storage_capacity, "supabase", fake)
    actions = []
    with storage_capacity.storage_upload_reservation(128):
        actions.append("upload")
    assert actions == ["upload"]
    assert fake.calls == [
        ("reserve_storage_upload", {"p_size_bytes": 128}),
        ("release_storage_upload", {"p_reservation_id": "22222222-2222-4222-8222-222222222222"}),
    ]


def test_global_capacity_rejects_without_upload(monkeypatch):
    fake = FakeSupabase({"allowed": False, "reason": "capacity_reached"})
    monkeypatch.setattr(storage_capacity, "supabase", fake)
    actions = []
    with pytest.raises(HTTPException) as exc:
        with storage_capacity.storage_upload_reservation(1024):
            actions.append("upload")
    assert exc.value.status_code == 507
    assert not actions
    assert len(fake.calls) == 1


@pytest.mark.parametrize("decision", [RuntimeError("provider failed"), {}, {"allowed": True, "reservation_id": "not-uuid"}])
def test_quota_query_fails_closed(monkeypatch, decision):
    fake = FakeSupabase(decision)
    monkeypatch.setattr(storage_capacity, "supabase", fake)
    with pytest.raises(HTTPException) as exc:
        with storage_capacity.storage_upload_reservation(512):
            pytest.fail("Upload executed without capacity verification")
    assert exc.value.status_code == 503


def test_invalid_size_is_rejected_before_rpc(monkeypatch):
    fake = FakeSupabase({"allowed": True})
    monkeypatch.setattr(storage_capacity, "supabase", fake)
    with pytest.raises(HTTPException) as exc:
        with storage_capacity.storage_upload_reservation(50 * 1024 * 1024 + 1):
            pass
    assert exc.value.status_code == 413
    assert fake.calls == []


def test_release_failure_does_not_mask_original_upload_error(monkeypatch):
    fake = FakeSupabase({"allowed": True, "reservation_id": "22222222-2222-4222-8222-222222222222"})
    fake.release_fails = True
    monkeypatch.setattr(storage_capacity, "supabase", fake)
    with pytest.raises(OSError, match="network"):
        with storage_capacity.storage_upload_reservation(50):
            raise OSError("network")


def test_admin_storage_snapshot_shows_aggregates_only(monkeypatch):
    class SnapshotSupabase:
        def rpc(self, name):
            assert name == "admin_storage_snapshot"
            return SimpleNamespace(execute=lambda: SimpleNamespace(data={
                "used_bytes": 450000, "reserved_bytes": 2000, "quota_bytes": 1073741824,
                "warning_percent": 75, "critical_percent": 85, "block_percent": 90,
                "buckets": [
                    {"bucket": "avatars", "objects": 1, "used_bytes": 280000, "name": "private-file.jpg"},
                    {"bucket": "post-media", "objects": 2, "used_bytes": 170000, "token": "private-token"},
                ],
                "personal": "private-user",
            }))
    monkeypatch.setattr(admin_metrics, "supabase", SnapshotSupabase())
    result = asyncio.run(admin_metrics._storage_snapshot())
    assert result.status == "available"
    assert result.used_bytes == 450000
    assert len(result.buckets) == 2
    assert "private-file.jpg" not in result.model_dump_json()
    assert "private-user" not in result.model_dump_json()
    assert "private-token" not in result.model_dump_json()


def test_storage_snapshot_does_not_fabricate_zero_when_missing(monkeypatch):
    class BadSupabase:
        def rpc(self, name):
            return SimpleNamespace(execute=lambda: SimpleNamespace(data={}))
    monkeypatch.setattr(admin_metrics, "supabase", BadSupabase())
    result = asyncio.run(admin_metrics._storage_snapshot())
    assert result.status == "unavailable"
    assert result.used_bytes is None

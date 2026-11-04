"""F4C1 — contrato mockado de cotas de publicação, sem rede social real."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api import plan_quotas
from api.routers import posts


def _quota_client(monkeypatch, error=None):
    client = MagicMock()
    if error:
        client.rpc.return_value.execute.side_effect = RuntimeError(error)
    else:
        client.rpc.return_value.execute.return_value = SimpleNamespace(data=1)
    monkeypatch.setattr(plan_quotas, "supabase", client)
    return client


def test_immediate_reservation_is_scoped_and_does_not_trust_client_tier(monkeypatch):
    client = _quota_client(monkeypatch)
    plan_quotas.reserve_post_plan_quota(
        "user-a", "profile-a", 71, immediate=True, reuse_existing=True,
    )
    name, payload = client.rpc.call_args.args
    assert name == "reserve_post_plan_quota"
    assert payload == {
        "p_user_id": "user-a", "p_profile_id": "profile-a",
        "p_post_id": 71, "p_kind": "immediate",
        "p_days": [], "p_times": [], "p_reuse_existing": True,
    }
    assert not any("tier" in key or "access" in key or "limit" in key for key in payload)


def test_recurring_reservation_sends_every_weekday_and_hour(monkeypatch):
    client = _quota_client(monkeypatch)
    plan_quotas.reserve_post_plan_quota(
        "user-a", "profile-b", 72, immediate=False,
        days=[0, 2, 6], times=["08:00", "12:30"],
    )
    payload = client.rpc.call_args.args[1]
    assert payload["p_kind"] == "recurring"
    assert payload["p_days"] == [0, 2, 6]
    assert payload["p_times"] == ["08:00", "12:30"]


@pytest.mark.parametrize("error,status_code,detail", [
    ("plan_immediate_quota_exceeded", 409, "imediatas"),
    ("plan_recurring_quota_exceeded", 409, "recorrentes"),
    ("profile_not_owned", 404, "não encontrado"),
    ("post_not_owned", 404, "não encontrado"),
    ("plan_policy_unavailable", 503, "indisponível"),
    ("connection failure", 503, "verificar"),
])
def test_quota_errors_fail_closed_without_leaking_db_text(monkeypatch, error, status_code, detail):
    _quota_client(monkeypatch, error)
    with pytest.raises(HTTPException) as raised:
        plan_quotas.reserve_post_plan_quota("user-a", "profile-a", 71, immediate=True)
    assert raised.value.status_code == status_code
    assert detail in raised.value.detail
    assert error not in raised.value.detail


def test_failed_creation_release_is_best_effort(monkeypatch):
    client = _quota_client(monkeypatch)
    plan_quotas.release_failed_post_plan_quota("user-a", "profile-a", 71)
    client.rpc.assert_called_once_with("release_failed_post_plan_quota", {
        "p_user_id": "user-a", "p_profile_id": "profile-a", "p_post_id": 71,
    })
    client.rpc.return_value.execute.side_effect = RuntimeError("database down")
    plan_quotas.release_failed_post_plan_quota("user-a", "profile-a", 71)


@pytest.mark.anyio
async def test_batch_reserves_per_network_and_blocks_excess_without_creating_jobs(monkeypatch):
    body = posts.PostBatchCreate(
        compositions=[
            {"network": "threads", "texts": ["Primeiro"]},
            {"network": "facebook", "texts": ["Segundo"]},
        ],
        product_ids=[],
        draft_media_ids=[],
        schedule={"trigger": "date", "run_date": "2099-01-01T12:00:00"},
        publish_immediately=True,
    )
    monkeypatch.setattr(posts, "_validate_product_ids", lambda *a: None)
    monkeypatch.setattr(posts, "_ensure_scheduler_available", AsyncMock())
    monkeypatch.setattr(posts, "_get_owned_ready_drafts", lambda *a: [])
    monkeypatch.setattr(posts, "_x_media_for", lambda *a: True)
    monkeypatch.setattr(posts, "_preview_batch", lambda *a: [
        {"network": "threads", "texts": ["Primeiro"], "mode": "text",
         "media_draft_ids": [], "warnings": []},
        {"network": "facebook", "texts": ["Segundo"], "mode": "text",
         "media_draft_ids": [], "warnings": []},
    ])
    next_id = iter((71, 72))
    monkeypatch.setattr(posts, "_create_thread", lambda *a: {"id": next(next_id)})
    monkeypatch.setattr(posts, "_set_post_products", lambda *a: None)
    monkeypatch.setattr(posts, "_attach_medias", lambda *a: [])
    create_jobs = AsyncMock()
    monkeypatch.setattr(posts, "_create_schedule_jobs", create_jobs)
    reserves = []
    def reserve(*args, **kwargs):
        reserves.append((args, kwargs))
        if args[2] == 72:
            raise HTTPException(status_code=409, detail="Limite de publicações imediatas por hora deste perfil atingido.")
    monkeypatch.setattr(posts, "reserve_post_plan_quota", reserve)
    rollback = MagicMock()
    release = MagicMock()
    monkeypatch.setattr(posts, "_rollback_plan", rollback)
    monkeypatch.setattr(posts, "release_failed_post_plan_quota", release)

    result = await posts.create_posts_batch(body, user_id="user-a", profile_id="profile-a")
    assert [r["post_id"] for r in result["created"]] == [71]
    assert [r["network"] for r in result["blocked"]] == ["facebook"]
    assert "Limite de publicações" in result["blocked"][0]["blocked_reason"]
    assert [args[0][2] for args in reserves] == [71, 72]
    create_jobs.assert_awaited_once()
    rollback.assert_called_once()
    release.assert_called_once_with("user-a", "profile-a", 72)


def test_migration_is_opt_in_private_and_reentrant():
    sql = (Path(__file__).resolve().parents[2] /
           "database/migrations/073_post_publication_plan_quotas.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS public.plan_immediate_dispatches" in sql
    assert "CREATE TABLE IF NOT EXISTS public.plan_recurring_slots" in sql
    assert "ON DELETE CASCADE" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FROM PUBLIC, anon, authenticated" in sql
    assert "TO service_role" in sql
    assert "FOR UPDATE" in sql
    assert "current_setting('app.profile_quota_rpc'" not in sql
    assert "CREATE TRIGGER" not in sql

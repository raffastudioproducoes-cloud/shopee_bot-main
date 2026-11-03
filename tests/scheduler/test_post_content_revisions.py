"""R12: revisão futura sem alterar conteúdo/resultado histórico.

Estes testes são isolados, não executam publicação nem chamam APIs reais.
"""
from pathlib import Path

import pytest

from shopee_bot.database import post_content_snapshot, publish_jobs
from shopee_bot.scheduler import publication_context


def test_migration_is_additive_and_exposes_no_client_write():
    sql = (
        Path(__file__).resolve().parents[2]
        / "database/migrations/069_post_content_revisions.sql"
    ).read_text(encoding="utf-8").lower()
    assert "create table if not exists public.post_content_revisions" in sql
    assert "alter table public.post_content_revisions enable row level security" in sql
    assert "revoke all on public.post_content_revisions from anon, authenticated" in sql
    assert "grant execute on function public.create_future_post_revision" in sql
    assert "to service_role" in sql
    assert "interval '30 minutes'" in sql
    assert "for update" in sql
    assert "drop table" not in sql
    assert "delete from public.posts" not in sql
    assert "update public.posts" not in sql
    assert "update public.schedulers" not in sql


def test_claim_freezes_original_slot_and_keeps_manual_retry_snapshot(monkeypatch):
    recorded = {}

    def fake_query(query, args, one=False):
        recorded.update(query=query.lower(), args=args)
        return {"id": "queue", "claim_token": "claim", "content_snapshot": None}

    monkeypatch.setattr(publish_jobs, "query_db", fake_query)
    publish_jobs.claim("queue", "worker", 600)
    query = recorded["query"]
    assert "job.status = 'pending'" in query
    assert "for update of job skip locked" in query
    assert "content_snapshot = coalesce(" in query
    assert "locked_candidate.original_slot > revision.effective_after" in query
    assert "original.content_snapshot as retry_snapshot" in query
    assert "when candidate.retry_source_id is not null" in query
    assert "original.user_id = locked_candidate.user_id" in query
    assert "original.profile_id is not distinct from locked_candidate.profile_id" in query
    assert "scheduled_for = coalesce(job.scheduled_for, candidate.original_slot)" in query
    assert recorded["args"] == ("queue", "production", "worker")


def test_snapshot_changes_only_active_claim_and_reverts_afterwards(monkeypatch):
    source = [
        {"id": 11, "text": "legado principal", "medias": [{"id": 4}],
         "product_ids": [99], "depth": 0},
        {"id": 12, "text": "legado reply", "medias": [], "product_ids": [], "depth": 1},
    ]
    snapshot = {
        "texts": ["novo texto", "novo reply", "terceira parte"],
        "product_ids": [100],
        "medias": [{"id": 7, "type": "IMAGE"}],
    }
    assert post_content_snapshot.apply_to_parts(source, post_content_snapshot.get()) is source
    token = publication_context.activate("job", "token", snapshot)
    try:
        current = post_content_snapshot.apply_to_parts(source, post_content_snapshot.get())
        assert [row["text"] for row in current] == snapshot["texts"]
        assert current[0]["medias"] == snapshot["medias"]
        assert current[1]["medias"] == []
        assert current[0]["product_ids"] == [100]
        assert source[0]["text"] == "legado principal"
        assert source[0]["medias"] == [{"id": 4}]
    finally:
        publication_context.reset(token)
    assert post_content_snapshot.get() is None


@pytest.mark.parametrize("bad_snapshot", [
    {"texts": [], "medias": [], "product_ids": []},
    {"texts": [""], "medias": [], "product_ids": []},
    {"texts": ["ok"], "medias": "wrong", "product_ids": []},
    {"texts": ["ok"], "medias": [], "product_ids": None},
])
def test_invalid_frozen_snapshot_blocks_external_delivery(bad_snapshot):
    with pytest.raises(ValueError, match="Snapshot de publicação inválido"):
        post_content_snapshot.apply_to_parts([{"text": "baseline"}], bad_snapshot)

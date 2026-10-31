"""Contrato da migration de grants e indices das FKs internas."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "database/migrations/056_harden_internal_grants_and_fk_indexes.sql"


def test_056_revokes_public_table_privileges_without_widening_rls():
    sql = MIGRATION.read_text(encoding="utf-8")
    statements = re.sub(r"--[^\n]*", "", sql).lower()
    normalized = " ".join(statements.split())
    assert (
        "revoke all privileges on table public.publication_claims, "
        "public.publish_jobs from anon, authenticated;"
    ) in normalized
    for forbidden in (" grant ", "create policy", "disable row level security", "truncate table", "drop table"):
        assert forbidden not in normalized


def test_056_covers_all_six_foreign_keys_idempotently():
    sql = re.sub(r"--[^\n]*", "", MIGRATION.read_text(encoding="utf-8"))
    expected = {
        "idx_publish_jobs_post_id": ("publish_jobs", "post_id"),
        "idx_publish_jobs_profile_id": ("publish_jobs", "profile_id"),
        "idx_publish_jobs_scheduler_id": ("publish_jobs", "scheduler_id"),
        "idx_publish_jobs_user_id": ("publish_jobs", "user_id"),
        "idx_revoked_sessions_user_id": ("revoked_sessions", "user_id"),
        "idx_temporary_media_uploads_profile_id": ("temporary_media_uploads", "profile_id"),
    }
    for name, (table, column) in expected.items():
        pattern = rf"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+{name}\s+ON\s+public\.{table}\s*\(\s*{column}\s*\)"
        assert re.search(pattern, sql, re.IGNORECASE), name

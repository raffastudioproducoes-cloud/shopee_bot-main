from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "database" / "migrations" / "035_create_profiles_table.sql"


def test_migration_file_exists_and_has_block_all_api_policy():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "create table if not exists public.profiles" in sql
    assert 'create policy "block_all_api" on public.profiles' in sql
    assert "on delete cascade" in sql


def test_migration_backfill_is_idempotent():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "where not exists" in sql

"""Invariantes da migração aditiva da chave de IA global."""

from pathlib import Path


def _migration() -> str:
    return (Path(__file__).resolve().parents[2] / "database" / "migrations"
            / "089_platform_ai_credentials.sql").read_text(encoding="utf-8").lower()


def test_platform_tables_are_idempotent_and_restricted():
    sql = _migration()
    assert "create table if not exists public.platform_ai_credentials" in sql
    assert "create table if not exists public.platform_ai_settings" in sql
    for name in ("platform_ai_credentials", "platform_ai_settings"):
        assert f"alter table public.{name} enable row level security" in sql
        assert f"tablename='{name}'" in sql
        assert f"create policy block_all_api on public.{name}" in sql
    assert "from public, anon, authenticated" in sql
    assert "to service_role" in sql
    assert "on conflict (environment, provider) do nothing" in sql
    assert "on conflict (environment) do nothing" in sql
    assert "foreign key (environment, active_provider)" in sql
    assert "('production'), ('staging')" in sql


def test_migration_copies_only_admin_ciphertext_without_exposing_it():
    sql = _migration()
    assert "cross join public.ai_credentials c" in sql
    assert "join public.users u on u.id = c.user_id" in sql
    assert "u.access = 'admin'" in sql
    assert "c.secret" in sql
    assert "decrypt(" not in sql
    assert "delete from" not in sql and "truncate" not in sql
    assert "drop table" not in sql
    assert "pg_cron" not in sql and "pg_net" not in sql

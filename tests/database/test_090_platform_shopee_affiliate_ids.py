"""Invariantes estáticas da migração 090, segredos globais e IDs individuais."""

from pathlib import Path


def _sql():
    return (Path(__file__).resolve().parents[2] / "database/migrations"
            / "090_platform_shopee_affiliate_ids.sql").read_text(encoding="utf-8").lower()


def test_090_is_additive_and_denies_public_access():
    sql = _sql()
    for table in ("platform_shopee_credentials", "shopee_affiliate_accounts"):
        assert f"create table if not exists public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
        assert f"create policy block_all_api on public.{table}" in sql
    assert "from public, anon, authenticated" in sql
    assert "to service_role" in sql
    assert "on conflict (environment) do nothing" in sql
    assert "user_id uuid primary key references public.users(id) on delete cascade" in sql
    assert "'production'), ('staging'" in sql


def test_090_backfills_only_admin_encrypted_secret_and_never_touches_jobs():
    sql = _sql()
    assert "cross join public.shopee_credentials c" in sql
    assert "join public.users u on u.id = c.user_id" in sql
    assert "u.access = 'admin'" in sql
    assert "c.secret" in sql
    for forbidden in ("decrypt(", "delete from", "truncate", "drop table", "pg_cron", "pg_net"):
        assert forbidden not in sql

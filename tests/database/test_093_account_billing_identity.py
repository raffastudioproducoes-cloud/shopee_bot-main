"""Contrato estático: identidade do titular restrita e migration sem quebra da main."""
from pathlib import Path


def test_migration_only_expands_private_identity_and_blocks_data_api():
    sql = (Path(__file__).resolve().parents[2] / "database/migrations"
           / "093_account_billing_identity.sql").read_text(encoding="utf-8").lower()
    assert "create table if not exists public.account_billing_identity" in sql
    assert "user_id uuid primary key references public.users(id) on delete cascade" in sql
    assert "cpf_ciphertext text" in sql and "cpf_fingerprint text unique" in sql
    assert "alter table public.account_billing_identity enable row level security" in sql
    assert "create policy block_all_api on public.account_billing_identity" in sql
    assert "from public, anon, authenticated" in sql
    assert "to service_role" in sql
    assert "alter table public.pending_auth_registrations add column if not exists" in sql
    for forbidden in ("drop table", "truncate", "delete from", "pg_cron", "pg_net", "alter table public.users"):
        assert forbidden not in sql

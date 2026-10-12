"""Migrações 038/039: profile_id nas demais tabelas e relaxamento de UNIQUE."""
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "database" / "migrations"
SQL_038 = (MIGRATIONS / "038_add_profile_id_to_remaining_tables.sql").read_text(encoding="utf-8")
SQL_039 = (MIGRATIONS / "039_relax_unique_for_multi_profile.sql").read_text(encoding="utf-8")

TABLES = [
    "shopee_credentials", "threads_credentials", "x_credentials", "facebook_credentials",
    "instagram_credentials", "tiktok_credentials", "kwai_credentials", "credential_checks",
    "posts", "medias", "schedulers", "activities", "request_logs", "audit_events",
]


def test_038_covers_every_table_idempotently_with_set_null():
    for table in TABLES:
        assert (
            f"alter table public.{table} add column if not exists profile_id uuid "
            "references profiles(id) on delete set null"
        ) in SQL_038
        assert f"create index if not exists idx_{table}_profile_id on public.{table}" in SQL_038
        assert f"update public.{table} t" in SQL_038


def test_038_is_additive_only():
    statements = [
        line.strip().lower() for line in SQL_038.splitlines()
        if line.strip() and not line.startswith("--")
    ]
    assert all(
        line.startswith(("alter table", "create index", "update", "set ", "from", "where"))
        for line in statements
    )
    assert "on delete cascade" not in SQL_038.lower()


def test_038_backfills_principal_only_where_null():
    assert SQL_038.count("pr.kind = 'principal' and t.profile_id is null") == len(TABLES)


def test_039_is_idempotent_and_touches_only_two_constraints():
    assert "drop constraint if exists shopee_credentials_app_id_key" in SQL_039
    assert "drop constraint if exists credential_checks_user_id_network_key" in SQL_039
    assert "create unique index if not exists uq_credential_checks_user_profile_network" in SQL_039


def test_040_recreates_unique_index_with_coalesce_and_dedupes_nulls():
    sql = (MIGRATIONS / "040_credential_checks_unique_coalesce.sql").read_text(encoding="utf-8")
    assert "drop index if exists public.uq_credential_checks_user_profile_network" in sql
    assert "create unique index if not exists uq_credential_checks_user_profile_network" in sql
    assert "coalesce(profile_id, '00000000-0000-0000-0000-000000000000'::uuid)" in sql
    assert sql.index("delete from") < sql.index("create unique index")


def test_047_adds_multi_day_recurrence_without_removing_legacy_day():
    sql = (MIGRATIONS / "047_add_scheduler_days_of_week.sql").read_text(encoding="utf-8").lower()
    assert "add column if not exists days_of_week smallint[]" in sql
    assert "cardinality(days_of_week) between 1 and 7" in sql
    assert "array[day_of_week]" in sql

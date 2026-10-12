"""Contrato estático da migration 045.

As migrations deste repositório não possuem um banco efêmero próprio. Este
teste mantém a cobertura verificável usada pelas migrations anteriores sem
carregar o conftest legado, que inicializa Postgres local.
"""
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "migrations"
    / "045_share_account_catalog_credentials.sql"
)


def _sql():
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_045_normalizes_catalog_and_credentials_by_account():
    sql = _sql()

    for table in ("products", "shopee_credentials", "ai_credentials"):
        assert f"update public.{table}" in sql
        assert "set profile_id = null" in sql

    assert "create unique index if not exists uq_products_user_product" in sql
    assert "on public.products (user_id, product_id)" in sql
    assert "create unique index if not exists uq_shopee_credentials_user" in sql
    assert "on public.shopee_credentials (user_id)" in sql
    assert "create unique index if not exists uq_ai_credentials_user_provider" in sql
    assert "on public.ai_credentials (user_id, provider)" in sql
    assert "create index if not exists idx_ai_credentials_user_id" in sql


def test_045_rejects_divergent_duplicates_before_mutating_data():
    sql = _sql()
    conflicts = (
        "migration 045 blocked: conflicting account-owned products",
        "migration 045 blocked: conflicting account-owned shopee credentials",
        "migration 045 blocked: conflicting account-owned ai credentials",
    )

    first_mutation = min(
        sql.index("drop index if exists public.uq_products_user_product_profile"),
        sql.index("drop index if exists public.uq_ai_credentials_user_profile_provider"),
        sql.index("update public.products"),
        sql.index("update public.shopee_credentials"),
        sql.index("update public.ai_credentials"),
    )
    assert sql.lstrip().startswith("begin;")
    assert sql.rstrip().endswith("commit;")
    assert all(sql.index(message) < first_mutation for message in conflicts)

    for table, identity in (
        ("products", "user_id, product_id"),
        ("shopee_credentials", "user_id"),
        ("ai_credentials", "user_id, provider"),
    ):
        assert f"from public.{table}" in sql
        assert identity in sql


def test_045_repoints_list_and_post_product_references_before_deduplication():
    sql = _sql()

    list_reference = sql.index("update public.product_lists_products")
    post_reference = sql.index("update public.posts_products")
    product_delete = sql.index("delete from public.products")
    assert list_reference < product_delete
    assert post_reference < product_delete

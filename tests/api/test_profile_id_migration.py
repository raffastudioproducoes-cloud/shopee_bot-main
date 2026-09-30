"""
Regression tests for migration 036: profile_id column addition to products and product_lists
"""
from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "database" / "migrations" / "036_add_profile_id_to_products_and_lists.sql"


def test_migration_adds_nullable_profile_id_with_set_null():
    """Verify migration adds profile_id as nullable with on delete set null"""
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "add column if not exists profile_id uuid" in sql
    assert "on delete set null" in sql
    assert "on delete cascade" not in sql


def test_migration_backfills_from_principal_profile():
    """Verify migration backfills profile_id from principal profiles"""
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "kind = 'principal'" in sql

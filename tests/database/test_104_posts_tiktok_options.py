"""Contrato da migração 104: só adiciona uma coluna anulável em posts, idempotente."""
from pathlib import Path

SQL = (Path(__file__).resolve().parents[2] / "database" / "migrations"
       / "104_posts_tiktok_options.sql").read_text(encoding="utf-8")
BODY = "\n".join(line for line in SQL.splitlines() if not line.strip().startswith("--"))
UPPER = BODY.upper()


def test_additive_and_idempotent():
    assert UPPER.count("ADD COLUMN IF NOT EXISTS") == 1
    assert "ALTER TABLE PUBLIC.POSTS" in UPPER
    assert "TIKTOK_OPTIONS JSONB" in UPPER
    assert "JSONB_TYPEOF(TIKTOK_OPTIONS) = 'OBJECT'" in UPPER
    for word in ("DROP ", "DELETE FROM", "TRUNCATE", "NOT NULL", "DEFAULT ", "CREATE TABLE",
                 "GRANT ", "DISABLE ROW LEVEL SECURITY", "FUNCTION"):
        assert word not in UPPER, word


def test_transaction_lock_timeout_and_rollback_documented():
    assert UPPER.startswith("BEGIN;") and UPPER.rstrip().endswith("COMMIT;")
    assert "LOCK_TIMEOUT" in UPPER
    assert "DROP COLUMN IF EXISTS tiktok_options" in SQL and "DELETE FROM migrations" in SQL

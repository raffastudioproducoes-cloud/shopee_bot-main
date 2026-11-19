"""Contrato da migração 105: colunas aditivas de reconexão, idempotente, RLS como a 091."""
from pathlib import Path

SQL = (Path(__file__).resolve().parents[2] / "database" / "migrations"
       / "105_shopee_video_reconnect.sql").read_text(encoding="utf-8")
BODY = "\n".join(line for line in SQL.splitlines() if not line.strip().startswith("--"))
UPPER = BODY.upper()


def test_additive_and_idempotent():
    assert UPPER.count("ADD COLUMN IF NOT EXISTS") == 2
    assert UPPER.count("ALTER TABLE PUBLIC.SHOPEE_VIDEO_AUTHORIZATIONS") == 3
    assert "NEEDS_RECONNECT BOOLEAN NOT NULL DEFAULT FALSE" in UPPER
    assert "RECONNECT_REASON TEXT" in UPPER
    for word in ("DROP ", "DELETE FROM", "TRUNCATE", "CREATE TABLE", "UPDATE ",
                 "DISABLE ROW LEVEL SECURITY", "FUNCTION", "CREATE POLICY"):
        assert word not in UPPER, word


def test_rls_and_grants_follow_091():
    assert "ENABLE ROW LEVEL SECURITY" in UPPER
    assert "REVOKE ALL ON TABLE PUBLIC.SHOPEE_VIDEO_AUTHORIZATIONS FROM PUBLIC, ANON, AUTHENTICATED" in UPPER
    assert "TO SERVICE_ROLE" in UPPER
    assert "TO ANON" not in UPPER and "TO AUTHENTICATED" not in UPPER


def test_transaction_lock_timeout_and_rollback_documented():
    assert UPPER.startswith("BEGIN;") and "COMMIT;" in UPPER
    assert "LOCK_TIMEOUT" in UPPER
    assert "DROP COLUMN IF EXISTS needs_reconnect" in SQL
    assert "DELETE FROM migrations WHERE name = '105_shopee_video_reconnect.sql'" in SQL

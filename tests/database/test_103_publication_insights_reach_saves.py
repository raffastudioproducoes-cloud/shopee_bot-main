"""Contrato da migração 103: só adiciona duas colunas anuláveis, idempotente, RLS fechada."""
from pathlib import Path

SQL = (Path(__file__).resolve().parents[2] / "database" / "migrations"
       / "103_publication_insights_reach_saves.sql").read_text(encoding="utf-8")
BODY = "\n".join(line for line in SQL.splitlines() if not line.strip().startswith("--"))
UPPER = BODY.upper()


def test_additive_and_idempotent():
    assert UPPER.count("ADD COLUMN IF NOT EXISTS") == 2
    assert "REACH BIGINT CHECK (REACH IS NULL OR REACH >= 0)" in UPPER
    assert "SAVES BIGINT CHECK (SAVES IS NULL OR SAVES >= 0)" in UPPER
    for word in ("DROP ", "DELETE FROM", "TRUNCATE", "NOT NULL", "DEFAULT ", "CREATE TABLE"):
        assert word not in UPPER, word


def test_rls_stays_closed_and_rollback_documented():
    assert "ENABLE ROW LEVEL SECURITY" in UPPER
    assert "FROM PUBLIC, anon, authenticated" in BODY
    assert "TO anon" not in BODY and "TO authenticated" not in BODY
    assert "DROP COLUMN IF EXISTS reach" in SQL and "DELETE FROM migrations" in SQL

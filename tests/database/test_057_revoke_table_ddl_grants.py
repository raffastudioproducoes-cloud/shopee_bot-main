"""Contrato de menor privilegio: sem revogar CRUD de consumidores legados."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "database/migrations/057_revoke_table_ddl_grants.sql"


def test_057_only_removes_admin_table_privileges():
    sql = MIGRATION.read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*", "", sql)
    normalized = " ".join(sql.lower().split())
    assert "revoke truncate, references, trigger on table" in normalized
    assert "from anon, authenticated;" in normalized
    assert "revoke all" not in normalized
    assert "revoke select" not in normalized
    assert "revoke insert" not in normalized
    assert "revoke update" not in normalized
    assert "revoke delete" not in normalized
    assert "grant " not in normalized


def test_057_covers_exactly_audited_legacy_tables():
    sql = MIGRATION.read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*", "", sql)
    body = sql.split("ON TABLE", 1)[1].split("FROM anon", 1)[0]
    tables = set(re.findall(r"public\.([a-z_]+)", body))
    assert len(tables) == 26
    assert {"users", "posts", "migrations", "schedulers", "ai_credentials"} <= tables
    assert "publish_jobs" not in tables
    assert "publication_claims" not in tables

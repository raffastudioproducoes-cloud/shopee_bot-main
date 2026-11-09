"""Contrato da migração 096: só índices, de forma idempotente e sem tocar em dados ou permissões."""
import re
from pathlib import Path

SQL = (Path(__file__).resolve().parents[2] / "database" / "migrations" / "096_performance_indexes.sql").read_text(encoding="utf-8")
BODY = "\n".join(line for line in SQL.splitlines() if not line.strip().startswith("--"))


def test_only_idempotent_index_statements():
    statements = [s.strip() for s in BODY.split(";") if s.strip()]
    allowed = re.compile(r"^(BEGIN|COMMIT|SET LOCAL lock_timeout = '10s'|CREATE INDEX IF NOT EXISTS [a-z0-9_]+\s+ON public\.[a-z_]+ \()", re.S)
    bad = [s[:80] for s in statements if not allowed.match(s)]
    assert not bad, bad


def test_no_destructive_or_privilege_changes():
    for word in ("DROP ", "DELETE ", "UPDATE ", "ALTER ", "GRANT ", "REVOKE ", "TRUNCATE", "CONCURRENTLY", "INSERT "):
        assert word not in BODY.upper(), word


def test_covers_post_listing_queries():
    assert "ON public.posts (user_id, profile_id, created_at DESC) WHERE post_id IS NULL" in BODY
    assert "ON public.publish_jobs (post_id, created_at DESC, id DESC)" in BODY
    assert "((metadata->>'post_id'), activity_id, created_at DESC)" in BODY

"""Contrato da migração 101: aditiva, idempotente, RLS fechada e sem tocar no que a main lê."""
from pathlib import Path

SQL = (Path(__file__).resolve().parents[2] / "database" / "migrations" / "101_post_metrics.sql").read_text(encoding="utf-8")
BODY = "\n".join(line for line in SQL.splitlines() if not line.strip().startswith("--"))
UPPER = BODY.upper()


def test_only_creates_new_objects_idempotently():
    assert UPPER.count("CREATE TABLE IF NOT EXISTS") == UPPER.count("CREATE TABLE") == 3
    assert all(line.startswith("CREATE INDEX IF NOT EXISTS") for line in
               (l.strip().upper() for l in BODY.splitlines()) if line.startswith("CREATE INDEX"))
    assert "CREATE OR REPLACE FUNCTION PUBLIC.RECORD_POST_LINK_CLICK" in UPPER
    for word in ("DROP ", "DELETE FROM", "TRUNCATE", "ALTER TABLE PUBLIC.PUBLICATION_INSIGHTS",
                 "ALTER TABLE PUBLIC.PUBLISH_JOBS", "ALTER TABLE PUBLIC.POSTS "):
        assert word not in UPPER, word


def test_rls_closed_and_only_service_role():
    for table in ("post_metrics", "post_link_clicks", "post_link_click_days"):
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in BODY
    assert "FROM PUBLIC, anon, authenticated" in BODY
    assert "TO anon" not in BODY and "TO authenticated" not in BODY
    assert "GRANT EXECUTE ON FUNCTION public.record_post_link_click(text) TO service_role" in BODY
    assert "block_all_api" in BODY and "USING (false) WITH CHECK (false)" in BODY


def test_required_columns_indexes_and_no_personal_data():
    for column in ("window_label", "views bigint", "reach bigint", "likes bigint", "comments bigint",
                   "shares bigint", "saves bigint", "clicks bigint", "extra jsonb", "source text",
                   "status text", "error text"):
        assert column in BODY, column
    assert "ON public.post_metrics (user_id, network, collected_at DESC)" in BODY
    assert "ON public.post_metrics (post_id, network, collected_at DESC)" in BODY
    assert "token ~ '^[A-Za-z0-9_-]{22,64}$'" in BODY and "LIKE 'https://%'" in BODY
    for forbidden in ("ip ", "ip_", "user_agent", "inet"):
        assert forbidden not in BODY.lower(), forbidden


def test_rollback_documented():
    assert "DROP TABLE IF EXISTS public.post_metrics;" in SQL
    assert "DROP FUNCTION IF EXISTS public.record_post_link_click(text);" in SQL

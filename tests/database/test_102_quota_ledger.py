"""Contrato estático da 102: livro de consumo aditivo, idempotente, imutável e fechado."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = (ROOT / "database/migrations/102_quota_ledger.sql").read_text(encoding="utf-8")
BODY = "\n".join(line for line in SQL.splitlines() if not line.strip().startswith("--"))
UPPER = BODY.upper()


def test_additive_and_idempotent():
    assert UPPER.count("CREATE TABLE IF NOT EXISTS") == UPPER.count("CREATE TABLE") == 2
    assert "ON CONFLICT (ID) DO NOTHING" in UPPER
    for word in ("DROP TABLE", "DROP FUNCTION", "TRUNCATE PUBLIC", "ALTER TABLE PUBLIC.POSTS",
                 "ALTER TABLE PUBLIC.PLAN_RECURRING_SLOTS", "ALTER TABLE PUBLIC.USERS"):
        assert word not in UPPER, word
    assert UPPER.count("DROP TRIGGER IF EXISTS") == UPPER.count("CREATE TRIGGER")


def test_ledger_has_no_cascading_foreign_keys():
    table = BODY[BODY.index("CREATE TABLE IF NOT EXISTS public.quota_ledger ("):]
    table = table[:table.index(");")]
    assert "REFERENCES" not in table.upper()


def test_closed_and_immutable():
    assert "FROM PUBLIC, anon, authenticated, service_role" in BODY
    assert "GRANT SELECT ON TABLE public.quota_ledger, public.quota_ledger_cutover TO service_role" in BODY
    assert not re.search(r"GRANT [^;]*(INSERT|UPDATE|DELETE)[^;]*quota_ledger", BODY)
    assert "TO anon" not in BODY and "TO authenticated" not in BODY
    assert "BEFORE UPDATE OR DELETE ON public.quota_ledger" in BODY
    assert "BEFORE TRUNCATE ON public.quota_ledger" in BODY
    assert BODY.count("USING (false) WITH CHECK (false)") == 2


def test_definer_functions_pin_search_path_and_keep_073_signatures():
    for header in re.findall(r"SECURITY DEFINER[^\n]*", BODY):
        assert "SET search_path = ''" in header
    assert ("public.reserve_post_plan_quota(\n    p_user_id uuid,\n    p_profile_id uuid,\n"
            "    p_post_id integer,\n    p_kind text,") in BODY
    assert ("release_failed_post_plan_quota(\n    p_user_id uuid, p_profile_id uuid, "
            "p_post_id integer\n) RETURNS integer") in BODY
    assert "IF p_amount IS NULL OR p_amount <= 0 THEN" in BODY


def test_rollback_documented():
    assert "DROP TABLE IF EXISTS public.quota_ledger;" in SQL
    assert "DROP TRIGGER IF EXISTS trg_plan_recurring_slots_ledger_release" in SQL

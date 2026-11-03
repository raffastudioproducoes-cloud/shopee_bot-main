"""Contratos estaticos da proposta F4E-1. NAO substituem PostgreSQL real."""
from pathlib import Path
import re
import unittest

SQL = (Path(__file__).resolve().parents[2] / "database/migrations/074_f4e1_inert_campaign_reservations.sql").read_text().lower()


class TestF4eProposal(unittest.TestCase):
    def test_proposal_is_outside_boot_migrations(self):
        self.assertNotIn("database/migrations/074_f4e1_inert_proposal.sql", SQL)

    def test_no_dispatch_writes(self):
        self.assertNotRegex(SQL, r"insert\s+into\s+(?:public\.)?(?:posts|schedulers|publish_jobs)\b")
        self.assertEqual(SQL.count("create trigger"), 1)
        self.assertIn("create trigger trg_guard_campaign_reservation_f4e", SQL)
        self.assertEqual(SQL.count("check (dispatch_enabled = false)"), 2)

    def test_bounded_states_and_lock(self):
        self.assertIn("'reserved_no_dispatch','released'", SQL)
        self.assertIn("'planned','cancelled'", SQL)
        self.assertIn("for update", SQL)
        self.assertIn("idempotency_conflict", SQL)
        self.assertIn("active_campaigns_per_profile", SQL)

    def test_role_boundary(self):
        self.assertEqual(SQL.count("security invoker"), 3)
        self.assertIn("from public, anon, authenticated, service_role", SQL)
        self.assertIn("from public,anon,authenticated,service_role", SQL)
        self.assertNotIn("security definer", SQL)
        self.assertNotIn("alter default privileges", SQL)


if __name__ == "__main__":
    unittest.main()

"""Contrato estático F4E-2B2: a proposta SQL nunca entra no migrador automático.

Não executa DDL em Supabase; revisões transacionais em PostgreSQL ficam
pendentes até autorização expressa e proteção dos dois executores.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "docs/sql-proposals/F4E2B2-INERT-CAMPAIGN-DISPATCH-LINKS.sql"
SQL = PROPOSAL.read_text(encoding="utf-8").lower()


class TestF4e2b2InertIdentity(unittest.TestCase):
    def test_outside_boot_migrations_with_immutable_identity(self):
        self.assertTrue(PROPOSAL.is_file())
        self.assertNotIn("database/migrations/", str(PROPOSAL))
        for column in (
            "reservation_id uuid not null", "occurrence_id uuid not null",
            "scheduler_id uuid not null", "publish_job_id uuid not null",
            "post_id integer not null", "user_id uuid not null",
            "profile_id uuid not null", "source_environment text not null",
            "network text not null",
        ):
            self.assertIn(column, SQL)
        self.assertIn("unique (occurrence_id, network)", SQL)
        self.assertIn("unique (publish_job_id)", SQL)
        self.assertIn("if tg_op <> 'insert'", SQL)

    def test_no_dispatch_or_activation_permissions(self):
        self.assertIn("check (status = 'inert')", SQL)
        self.assertIn("check (dispatch_enabled = false)", SQL)
        self.assertIn("grant select on public.campaign_dispatch_links_f4e to service_role", SQL)
        self.assertNotRegex(SQL, r"grant\s+(?:insert|update|delete|all)\s+on")
        self.assertNotRegex(SQL, r"insert\s+into\s+(?:public\.)?(?:posts|schedulers|publish_jobs)\b")
        self.assertNotIn("security definer", SQL)
        self.assertNotIn("alter default privileges", SQL)

    def test_ownership_and_cross_environment_validation(self):
        for predicate in (
            "reservation.user_id = new.user_id", "reservation.profile_id = new.profile_id",
            "occurrence.reservation_id = new.reservation_id",
            "schedule.environment = new.source_environment",
            "schedule.profile_id = new.profile_id",
            "post.profile_id = new.profile_id",
            "job.scheduler_id = new.scheduler_id", "job.post_id = new.post_id",
            "job.network = new.network", "job.status = 'pending'",
            "job.external_started_at is null",
        ):
            self.assertIn(predicate, SQL)
        self.assertIn("enable row level security", SQL)
        self.assertRegex(SQL, r"revoke\s+all\s+on\s+table[\s\S]+?anon, authenticated, service_role")


if __name__ == "__main__":
    unittest.main()

"""Integration contracts ONLY against the disposable local CI service."""
import json
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg

DSN = "postgresql://postgres:postgres@127.0.0.1:5432/f4e_test"
ROOT = Path(__file__).resolve().parents[2]


class TestF4ePostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("F4E_DISPOSABLE_DSN") != DSN:
            raise RuntimeError("Run only with the exact disposable CI service DSN")
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute((ROOT / "tests/sql/f4e1_fixture.sql").read_text())
            con.execute((ROOT / "docs/sql-proposals/074_f4e1_inert_proposal.sql").read_text())

    def setUp(self):
        self.user, self.profile = uuid.uuid4(), uuid.uuid4()
        self.drafts = [uuid.uuid4() for _ in range(4)]
        self.instant = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
        local = self.instant - timedelta(hours=3)
        self.start = local.date()
        with psycopg.connect(DSN) as con:
            con.execute("INSERT INTO public.users VALUES (%s,'USER','pro')", (self.user,))
            con.execute("INSERT INTO public.profiles VALUES (%s,%s)", (self.profile, self.user))
            for draft in self.drafts:
                con.execute(
                    "INSERT INTO public.campaign_drafts VALUES (%s,%s,%s,1,'draft','[]',%s::jsonb)",
                    (draft, self.user, self.profile, json.dumps({
                        "start_date": str(self.start), "end_date": str(self.start + timedelta(days=14))
                    })),
                )

    def reserve(self, draft, key, values=None, user=None, profile=None):
        values = values if values is not None else [self.instant.strftime("%Y-%m-%dT%H:%M:%SZ")]
        with psycopg.connect(DSN) as con:
            con.execute("SET LOCAL ROLE service_role")
            return con.execute(
                "SELECT public.reserve_campaign_f4e(%s,%s,%s,1,%s,%s::jsonb)",
                (user or self.user, profile or self.profile, draft, key, json.dumps(values)),
            ).fetchone()[0]

    def test_idempotency_release_and_duplicate_revision(self):
        rid = self.reserve(self.drafts[0], "first")
        self.assertEqual(rid, self.reserve(self.drafts[0], "first"))
        with self.assertRaises(psycopg.Error):
            self.reserve(self.drafts[1], "first")
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.reserve(self.drafts[0], "different")
        with psycopg.connect(DSN) as con:
            con.execute("SET LOCAL ROLE service_role")
            self.assertTrue(con.execute("SELECT public.release_campaign_f4e(%s,%s,%s)",
                                        (self.user, self.profile, rid)).fetchone()[0])
            self.assertEqual(con.execute("SELECT status FROM public.campaign_occurrences_f4e WHERE reservation_id=%s",
                                         (rid,)).fetchone()[0], "cancelled")
        self.assertEqual(rid, self.reserve(self.drafts[0], "first"))
        self.reserve(self.drafts[0], "new-after-release")

    def test_timestamp_window_and_atomic_failure(self):
        for invalid in ("2030-01-01T00:00:00", "2000-01-01T00:00:00Z",
                        (self.instant + timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "not-a-date"):
            with self.subTest(invalid=invalid), self.assertRaises(psycopg.Error):
                self.reserve(self.drafts[0], str(uuid.uuid4()), [invalid])
        with psycopg.connect(DSN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM public.campaign_reservations_f4e WHERE user_id=%s",
                                         (self.user,)).fetchone()[0], 0)

    def test_quota_concurrency_last_slot(self):
        self.reserve(self.drafts[0], "first")
        def attempt(i):
            try:
                self.reserve(self.drafts[i], "race-" + str(i))
                return True
            except psycopg.Error:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt, (1, 2))), [False, True])
        with psycopg.connect(DSN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM public.campaign_reservations_f4e WHERE user_id=%s",
                                         (self.user,)).fetchone()[0], 2)

    def test_acl_and_cross_profile(self):
        with psycopg.connect(DSN) as con:
            for role in ("anon", "authenticated"):
                self.assertFalse(con.execute(
                    "SELECT has_table_privilege(%s,'public.campaign_reservations_f4e','SELECT')", (role,)
                ).fetchone()[0])
                self.assertFalse(con.execute(
                    "SELECT has_function_privilege(%s, 'public.reserve_campaign_f4e(uuid,uuid,uuid,integer,text,jsonb)', 'EXECUTE')",
                    (role,),
                ).fetchone()[0])
            self.assertTrue(con.execute(
                "SELECT relrowsecurity FROM pg_class WHERE oid='public.campaign_reservations_f4e'::regclass"
            ).fetchone()[0])
        with self.assertRaises(psycopg.Error):
            self.reserve(self.drafts[0], "bad-owner", profile=uuid.uuid4())

    def test_slot_cap_and_free(self):
        values = [(self.instant + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
                  for i in range(4)]
        with self.assertRaises(psycopg.Error):
            self.reserve(self.drafts[0], "four-slots", values)
        with psycopg.connect(DSN) as con:
            con.execute("UPDATE public.users SET plan_tier='free' WHERE id=%s", (self.user,))
        with self.assertRaises(psycopg.Error):
            self.reserve(self.drafts[0], "free")


if __name__ == "__main__":
    unittest.main()

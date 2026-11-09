"""Contratos F4E de reserva por rede/dia em PostgreSQL 16 descartavel."""
import json
import os
import re
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg import sql


DSN = "postgresql://postgres:postgres@127.0.0.1:5432/f4e_test"
ROOT = Path(__file__).resolve().parents[2] / "database/migrations"


class TestCampaignNetworkReservations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("F4E_DISPOSABLE_DSN") != DSN:
            raise RuntimeError("Banco compartilhado ou de producao proibido")
        cls.database = "f4e_net_" + uuid.uuid4().hex
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database)))
        cls.addClassCleanup(cls.drop_database)
        with cls.connect(autocommit=True) as con:
            for role in ("anon", "authenticated", "service_role"):
                con.execute(
                    "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='"
                    + role + "') THEN CREATE ROLE " + role + "; END IF; END $$"
                )
            con.execute("""
                CREATE TABLE public.users (
                  id uuid PRIMARY KEY, access text NOT NULL, plan_tier text NOT NULL
                );
                CREATE TABLE public.profiles (
                  id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES public.users(id)
                );
                CREATE TABLE public.plan_limits (
                  tier text PRIMARY KEY, active_campaigns_per_profile integer,
                  campaign_days integer, campaign_posts_per_day integer
                );
                CREATE TABLE public.product_lists (
                  id integer PRIMARY KEY, user_id uuid NOT NULL REFERENCES public.users(id),
                  profile_id uuid NOT NULL REFERENCES public.profiles(id)
                );
                CREATE TABLE public.products (
                  id integer PRIMARY KEY, user_id uuid NOT NULL REFERENCES public.users(id)
                );
                CREATE TABLE public.posts (
                  id integer PRIMARY KEY, user_id uuid NOT NULL REFERENCES public.users(id)
                );
                CREATE TABLE public.schedulers (
                  id uuid PRIMARY KEY, post_id integer REFERENCES public.posts(id)
                );
                CREATE TABLE public.publish_jobs (
                  id uuid PRIMARY KEY, scheduler_id uuid REFERENCES public.schedulers(id),
                  status text NOT NULL DEFAULT 'pending',
                  finished_at timestamptz, last_error text
                );
                INSERT INTO public.plan_limits VALUES
                  ('free',0,0,0),('pro',2,15,3),('premium',5,30,15);
                GRANT USAGE ON SCHEMA public TO anon,authenticated,service_role;
                GRANT SELECT,UPDATE ON public.users TO service_role;
                GRANT SELECT ON public.profiles,public.plan_limits,public.product_lists TO service_role;
                GRANT SELECT ON public.products TO service_role;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                  GRANT ALL ON TABLES TO service_role;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                  GRANT EXECUTE ON FUNCTIONS TO service_role;
            """)
            for name in (
                "070_campaign_drafts.sql", "071_campaign_names_and_media.sql",
                "074_f4e1_inert_campaign_reservations.sql",
                "075_campaign_publication_origin_guards.sql",
                "076_campaign_network_reservations.sql",
                "095_campaign_active_weekday_quota.sql",
            ):
                con.execute((ROOT / name).read_text())

    @classmethod
    def connect(cls, **kwargs):
        return psycopg.connect(DSN, dbname=cls.database, **kwargs)

    @classmethod
    def drop_database(cls):
        if not re.fullmatch(r"f4e_net_[0-9a-f]{32}", cls.database):
            raise RuntimeError("Nome de banco inesperado")
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(cls.database)))

    def setUp(self):
        self.user, self.profile = uuid.uuid4(), uuid.uuid4()
        self.instant = (datetime.now(timezone.utc) + timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)
        local_day = (self.instant - timedelta(hours=3)).date()
        self.start = local_day
        self.drafts = [uuid.uuid4() for _ in range(3)]
        self.product1, self.product2 = (self.user.int % 1000000000) + 1, (self.user.int % 1000000000) + 2
        with self.connect() as con:
            con.execute(
                "INSERT INTO users(id,access,plan_tier,campaign_paid_through) VALUES (%s,'USER','pro',now()+interval '30 days')",
                (self.user,),
            )
            con.execute("INSERT INTO profiles(id,user_id) VALUES (%s,%s)", (self.profile, self.user))
            for product_id in (self.product1, self.product2):
                con.execute(
                    "INSERT INTO products(id,user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (product_id, self.user),
                )
            for index, draft in enumerate(self.drafts):
                con.execute(
                    """INSERT INTO campaign_drafts
                       (id,user_id,profile_id,source_list_name,items,schedule)
                       VALUES (%s,%s,%s,'Fixture',%s::jsonb,%s::jsonb)""",
                    (draft, self.user, self.profile, json.dumps([
                        {"product_id": self.product1, "copy": "A",
                         "networks": ["threads"] if index == 1 else ["threads", "facebook"]},
                        {"product_id": self.product2, "copy": "B", "networks": ["threads"]},
                    ]), json.dumps({
                        "start_date": str(self.start),
                        "end_date": str(self.start + timedelta(days=14)),
                        "weekdays": [self.start.weekday()],
                    })),
                )

    def reserve(self, draft_index=0, values=None, key=None):
        values = values or [self.instant.strftime("%Y-%m-%dT%H:%M:%SZ")]
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            return con.execute(
                "SELECT public.reserve_campaign_networks_f4e(%s,%s,%s,1,%s,%s::jsonb)",
                (self.user, self.profile, self.drafts[draft_index],
                 key or str(uuid.uuid4()), json.dumps(values)),
            ).fetchone()[0]

    def set_schedule(self, draft_index, end_date, weekdays):
        schedule = {
            "start_date": str(self.start),
            "end_date": str(end_date),
            "weekdays": list(weekdays),
        }
        with self.connect() as con:
            con.execute(
                "UPDATE campaign_drafts SET schedule=%s::jsonb WHERE id=%s",
                (json.dumps(schedule), self.drafts[draft_index]),
            )

    def occurrences_for_days(self, end_date, weekdays):
        selected = set(weekdays)
        values = []
        for offset in range((end_date - self.start).days + 1):
            day = self.start + timedelta(days=offset)
            if day.weekday() in selected:
                values.append(
                    (self.instant + timedelta(days=offset)).strftime("%Y-%m-%dT%H:%M:%SZ")
                )
        return values

    def test_plan_quota_counts_selected_weekdays_not_calendar_days(self):
        end_date = self.start + timedelta(days=29)
        weekdays = [
            self.start.weekday(),
            (self.start.weekday() + 1) % 7,
            (self.start.weekday() + 3) % 7,
            (self.start.weekday() + 5) % 7,
        ]
        self.set_schedule(0, end_date, weekdays)
        occurrences = self.occurrences_for_days(end_date, weekdays)
        self.assertGreater(len(occurrences), 15)
        with self.assertRaises(psycopg.Error):
            self.reserve(values=occurrences, key="pro-weekday-limit")
        with self.connect() as con:
            con.execute(
                "UPDATE users SET plan_tier='premium',campaign_paid_through=now()+interval '250 days' WHERE id=%s",
                (self.user,),
            )
        self.assertIsInstance(
            self.reserve(values=occurrences, key="premium-weekday-limit"), uuid.UUID,
        )

    def test_thirty_active_weekdays_can_span_210_calendar_days(self):
        end_date = self.start + timedelta(days=209)
        weekdays = [self.start.weekday()]
        self.set_schedule(1, end_date, weekdays)
        occurrences = self.occurrences_for_days(end_date, weekdays)
        self.assertEqual(len(occurrences), 30)
        with self.connect() as con:
            con.execute(
                "UPDATE users SET plan_tier='premium',campaign_paid_through=now()+interval '250 days' WHERE id=%s",
                (self.user,),
            )
        self.assertIsInstance(
            self.reserve(draft_index=1, values=occurrences, key="premium-30-active-days"),
            uuid.UUID,
        )

    def test_network_slots_rotate_per_product_and_idempotency(self):
        a = self.instant.strftime("%Y-%m-%dT%H:%M:%SZ")
        b = (self.instant + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rid = self.reserve(values=[a, b], key="first")
        self.assertEqual(rid, self.reserve(values=[a, b], key="first"))
        with self.connect() as con:
            rows = con.execute(
                """SELECT s.product_id,s.network,s.content_text
                   FROM campaign_network_slots_f4e s
                   JOIN campaign_occurrences_f4e o ON o.id=s.occurrence_id
                   WHERE s.reservation_id=%s ORDER BY o.ordinal,s.network""",
                (rid,),
            ).fetchall()
        self.assertEqual(rows, [(self.product1, "facebook", "A"), (self.product1, "threads", "A"),
                                  (self.product2, "threads", "B")])

    def test_daily_network_quota_rejects_entire_transaction(self):
        a = self.instant.strftime("%Y-%m-%dT%H:%M:%SZ")
        b = (self.instant + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        c = (self.instant + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.assertRaises(psycopg.Error):
            self.reserve(values=[a,b,c])
        with self.connect() as con:
            self.assertEqual(con.execute(
                "SELECT count(*) FROM campaign_reservations_f4e WHERE user_id=%s", (self.user,)
            ).fetchone()[0], 0)

    def test_cross_campaign_quota_is_account_locked(self):
        self.reserve(key="one")
        a = (self.instant + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = (self.instant + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        # A segunda campanha com dois slots excede o saldo de 1 rede/dia.
        with self.assertRaises(psycopg.Error):
            self.reserve(draft_index=1, values=[a, b], key="two")
        self.assertEqual(self.reserve(draft_index=1, values=[a], key="valid"), self.reserve(
            draft_index=1, values=[a], key="valid"))

    def test_paid_period_required_but_admin_exempt(self):
        with self.connect() as con:
            con.execute("UPDATE users SET campaign_paid_through=now()-interval '1 day' WHERE id=%s", (self.user,))
        with self.assertRaises(psycopg.Error):
            self.reserve()
        with self.connect() as con:
            con.execute("UPDATE users SET access='ADMIN' WHERE id=%s", (self.user,))
        self.assertIsInstance(self.reserve(), uuid.UUID)

    def test_all_slots_must_be_inside_confirmed_paid_period(self):
        with self.connect() as con:
            con.execute(
                "UPDATE users SET campaign_paid_through=%s WHERE id=%s",
                (self.instant - timedelta(hours=1),self.user),
            )
        with self.assertRaises(psycopg.Error):
            self.reserve()

    def test_completed_attempt_still_consumes_daily_network_quota(self):
        rid = self.reserve()
        with self.connect() as con:
            con.execute(
                "UPDATE campaign_network_slots_f4e SET state='succeeded',finished_at=now() WHERE reservation_id=%s",
                (rid,),
            )
            con.execute(
                "UPDATE campaign_reservations_f4e SET lifecycle='completed',status='released',released_at=now() WHERE id=%s",
                (rid,),
            )
        with self.assertRaises(psycopg.Error):
            self.reserve(draft_index=0,values=[
                (self.instant+timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                (self.instant+timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ])

    def test_paid_downgrade_requires_cancelling_excess_before_resuming(self):
        with self.connect() as con:
            con.execute("UPDATE users SET plan_tier='premium' WHERE id=%s",(self.user,))
        reservations = [self.reserve(draft_index=i,key=f"downgrade-{i}") for i in range(3)]
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            direct_activation = con.execute(
                "SELECT has_function_privilege('service_role',"
                "'public.activate_campaign_networks_f4e(uuid,uuid,uuid,text)','EXECUTE')"
            ).fetchone()[0]
            for rid in reservations:
                if direct_activation:
                    con.execute(
                        "SELECT public.activate_campaign_networks_f4e(%s,%s,%s,'staging')",
                        (self.user,self.profile,rid),
                    )
                else:
                    con.execute("RESET ROLE")
                    con.execute("""
                        INSERT INTO campaign_oauth_checks_f4e(reservation_id,network)
                        SELECT DISTINCT reservation_id,network FROM campaign_network_slots_f4e
                        WHERE reservation_id=%s
                    """,(rid,))
                    con.execute("SET LOCAL ROLE service_role")
                    con.execute(
                        "SELECT public.materialize_campaign_f4e(%s,%s,%s,'staging')",
                        (self.user,self.profile,rid),
                    )
                con.execute(
                    "SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,'pause')",
                    (self.user,self.profile,rid),
                )
            con.execute("RESET ROLE")
            con.execute("UPDATE users SET plan_tier='pro' WHERE id=%s",(self.user,))
            con.execute("SET LOCAL ROLE service_role")
            with self.assertRaises(psycopg.Error):
                with con.transaction():
                    con.execute(
                        "SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,'resume')",
                        (self.user,self.profile,reservations[0]),
                    )
            self.assertEqual(con.execute(
                "SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,'cancel')",
                (self.user,self.profile,reservations[2]),
            ).fetchone()[0],"cancelled")
            self.assertEqual(con.execute(
                "SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,'resume')",
                (self.user,self.profile,reservations[0]),
            ).fetchone()[0],"active")

    def test_public_roles_cannot_reserve_or_read(self):
        with self.connect() as con:
            for role in ("anon","authenticated"):
                self.assertFalse(con.execute(
                    "SELECT has_function_privilege(%s, 'public.reserve_campaign_networks_f4e(uuid,uuid,uuid,integer,text,jsonb)','EXECUTE')", (role,)
                ).fetchone()[0])
                self.assertFalse(con.execute(
                    "SELECT has_table_privilege(%s,'public.campaign_network_slots_f4e','SELECT')", (role,)
                ).fetchone()[0])
            self.assertFalse(con.execute(
                "SELECT has_function_privilege('service_role','public.reserve_campaign_f4e(uuid,uuid,uuid,integer,text,jsonb)','EXECUTE')"
            ).fetchone()[0])

    def test_activate_pause_resume_cancel_and_history(self):
        rid = self.reserve()
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            self.assertTrue(con.execute(
                "SELECT public.activate_campaign_networks_f4e(%s,%s,%s,'staging')",
                (self.user, self.profile, rid),
            ).fetchone()[0])
            self.assertEqual(con.execute(
                "SELECT lifecycle,dispatch_enabled FROM campaign_reservations_f4e WHERE id=%s",
                (rid,),
            ).fetchone(), ("active", True))
            for action, expected in (("pause", "paused"), ("resume", "active"), ("cancel", "cancelled")):
                self.assertEqual(con.execute(
                    "SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,%s)",
                    (self.user, self.profile, rid, action),
                ).fetchone()[0], expected)
            self.assertEqual(con.execute(
                "SELECT count(*) FROM campaign_network_slots_f4e WHERE reservation_id=%s AND state='cancelled'",
                (rid,),
            ).fetchone()[0], 2)
            with self.assertRaises(psycopg.Error):
                with con.transaction():
                    con.execute(
                        "SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,'resume')",
                        (self.user, self.profile, rid),
                    )

    def test_expiry_blocks_activation_after_reservation(self):
        rid = self.reserve()
        with self.connect() as con:
            con.execute("UPDATE users SET campaign_paid_through=now()-interval '1 second' WHERE id=%s", (self.user,))
            con.execute("SET LOCAL ROLE service_role")
            with self.assertRaises(psycopg.Error):
                with con.transaction():
                    con.execute(
                        "SELECT public.activate_campaign_networks_f4e(%s,%s,%s,'production')",
                        (self.user, self.profile, rid),
                    )
            self.assertEqual(con.execute(
                "SELECT lifecycle FROM campaign_reservations_f4e WHERE id=%s", (rid,)
            ).fetchone()[0], "preparing")

"""Contrato real de origem F4E, isolado em banco descartavel PostgreSQL 16.

Nenhuma consulta ao Supabase real, nenhuma chamada externa.
"""
import os
import re
import unittest
import uuid
from pathlib import Path

import psycopg
from psycopg import sql


DSN = "postgresql://postgres:postgres@127.0.0.1:5432/f4e_test"
ROOT = Path(__file__).resolve().parents[2] / "database/migrations"


class TestF4e2b4OriginPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("F4E_DISPOSABLE_DSN") != DSN:
            raise RuntimeError("F4E requires the exact disposable CI DSN")
        cls.database = "f4e2b4_" + uuid.uuid4().hex
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database)))
        cls.addClassCleanup(cls.drop_database)
        with cls.connect(autocommit=True) as con:
            for role in ("anon", "authenticated", "service_role"):
                con.execute(
                    "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '"
                    + role + "') THEN CREATE ROLE " + role + "; END IF; END $$"
                )
            for name in (
                "001_create_users_table.sql", "002_create_products_table.sql",
                "003_create_product_lists_table.sql",
                "012_create_posts_table.sql", "017_create_schedulers_table.sql",
                "023_add_network_to_posts.sql", "035_create_profiles_table.sql",
                "053_create_publish_jobs.sql", "060_track_external_publish_start.sql",
                "061_guard_legacy_publish_leases.sql", "067_isolate_scheduler_environments.sql",
                "068_central_dispatch_compatibility.sql",
            ):
                con.execute((ROOT / name).read_text())
            for table in ("posts", "schedulers"):
                con.execute(
                    "ALTER TABLE public." + table
                    + " ADD COLUMN profile_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL"
                )
            con.execute((ROOT / "075_campaign_publication_origin_guards.sql").read_text())

    @classmethod
    def connect(cls, **kwargs):
        return psycopg.connect(DSN, dbname=cls.database, **kwargs)

    @classmethod
    def drop_database(cls):
        if not re.fullmatch(r"f4e2b4_[0-9a-f]{32}", cls.database):
            raise RuntimeError("Refusing to drop an unrecognized database")
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(cls.database)))

    def setUp(self):
        self.user = uuid.uuid4()
        with self.connect() as con:
            con.execute(
                "INSERT INTO users(id, username, password) VALUES (%s,%s,'fixture')",
                (self.user, str(self.user)),
            )
            self.profile = con.execute(
                "INSERT INTO profiles(user_id,kind,nome) VALUES (%s,'principal','fixture') RETURNING id",
                (self.user,),
            ).fetchone()[0]
            self.post = con.execute(
                "INSERT INTO posts(user_id,text,profile_id,network) VALUES (%s,'fixture',%s,'threads') RETURNING id",
                (self.user, self.profile),
            ).fetchone()[0]

    def add_schedule(self, con, origin=None):
        extra = ", publication_origin" if origin is not None else ""
        params = (self.post, self.user, self.profile)
        if origin is not None:
            params += (origin,)
        return con.execute(
            "INSERT INTO schedulers(post_id,user_id,profile_id,func,trigger"
            + extra
            + ") VALUES (%s,%s,%s,'bot_post','date'"
            + (",%s" if origin is not None else "")
            + ") RETURNING id",
            params,
        ).fetchone()[0]

    def add_job(self, con, schedule, origin=None):
        extra = ", publication_origin" if origin is not None else ""
        params = (schedule, self.post, self.user, self.profile, str(uuid.uuid4()))
        if origin is not None:
            params += (origin,)
        return con.execute(
            "INSERT INTO publish_jobs(scheduler_id,post_id,user_id,profile_id,network,idempotency_key"
            + extra
            + ") VALUES (%s,%s,%s,%s,'threads',%s"
            + (",%s" if origin is not None else "")
            + ") RETURNING id",
            params,
        ).fetchone()[0]

    def test_legacy_producer_and_claim_remain_compatible(self):
        with self.connect() as con:
            schedule = self.add_schedule(con)
            job = self.add_job(con, schedule)
            self.assertEqual(
                con.execute("SELECT publication_origin FROM publish_jobs WHERE id=%s", (job,)).fetchone()[0],
                "legacy",
            )
            con.execute("UPDATE publish_jobs SET status='running' WHERE id=%s", (job,))
            self.assertEqual(
                con.execute("SELECT status FROM publish_jobs WHERE id=%s", (job,)).fetchone()[0],
                "running",
            )

    def test_campaign_cannot_be_claimed_or_delivered(self):
        with self.connect() as con:
            schedule = self.add_schedule(con, "campaign")
            job = self.add_job(con, schedule, "campaign")
            for statement in (
                "UPDATE publish_jobs SET status='running' WHERE id=%s",
                "UPDATE publish_jobs SET external_started_at=now() WHERE id=%s",
                "UPDATE publish_jobs SET claim_token=gen_random_uuid() WHERE id=%s",
            ):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with con.transaction():
                        con.execute(statement, (job,))
            self.assertEqual(
                con.execute("SELECT status FROM publish_jobs WHERE id=%s", (job,)).fetchone()[0],
                "pending",
            )

    def test_main_old_job_insert_cannot_erase_campaign_origin(self):
        with self.connect() as con:
            schedule = self.add_schedule(con, "campaign")
            with self.assertRaises(psycopg.errors.CheckViolation):
                with con.transaction():
                    self.add_job(con, schedule)
            self.assertEqual(
                con.execute("SELECT count(*) FROM publish_jobs WHERE scheduler_id=%s", (schedule,)).fetchone()[0],
                0,
            )

    def test_origin_cannot_be_rewritten(self):
        with self.connect() as con:
            schedule = self.add_schedule(con)
            job = self.add_job(con, schedule)
            for table, ident in (("schedulers", schedule), ("publish_jobs", job)):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with con.transaction():
                        con.execute(
                            sql.SQL("UPDATE {} SET publication_origin='campaign' WHERE id=%s")
                            .format(sql.Identifier(table)),
                            (ident,),
                        )

    def test_null_and_unknown_origin_rejected(self):
        with self.connect() as con:
            schedule = self.add_schedule(con)
            for bad in (None, "unknown"):
                with self.assertRaises((psycopg.errors.NotNullViolation, psycopg.errors.CheckViolation)):
                    with con.transaction():
                        self.add_job(con, schedule, bad if bad is not None else "unknown")

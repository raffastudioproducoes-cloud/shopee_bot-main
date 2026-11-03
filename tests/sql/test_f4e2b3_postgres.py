"""F4E-2B3: proposta SQL real SOMENTE em PostgreSQL descartavel da CI.

Nao importa o app, nao acessa Supabase e nao executa publicadores.
O banco privado de teste usa migrations reais dos pais; apenas os ALTERs
de profile_id de 038 sao projetados porque as credenciais nao sao parte
deste contrato. Isto nao certifica o schema/deploy compartilhado completo.
"""
import os
import re
from pathlib import Path
import unittest
import uuid

import psycopg
from psycopg import sql

DSN = "postgresql://postgres:postgres@127.0.0.1:5432/f4e_test"
ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "docs/sql-proposals/F4E2B2-INERT-CAMPAIGN-DISPATCH-LINKS.sql"


class TestF4e2b3Postgres(unittest.TestCase):
    @classmethod
    def connect(cls, **kwargs):
        return psycopg.connect(DSN, dbname=cls.database, **kwargs)

    @classmethod
    def setUpClass(cls):
        if os.getenv("F4E_DISPOSABLE_DSN") != DSN:
            raise RuntimeError("Run only with the exact disposable CI service DSN")
        cls.database = "f4e2b3_" + uuid.uuid4().hex
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database)))
        cls.addClassCleanup(cls.drop_disposable_database)
        # Roles sao globais e ja foram criadas pela suite F4E1 neste job.
        names = [
            "001_create_users_table.sql", "002_create_products_table.sql",
            "003_create_product_lists_table.sql", "012_create_posts_table.sql",
            "017_create_schedulers_table.sql", "023_add_network_to_posts.sql",
            "035_create_profiles_table.sql", "036_add_profile_id_to_products_and_lists.sql",
            "044_add_group_id_to_posts.sql", "047_add_scheduler_days_of_week.sql",
            "053_create_publish_jobs.sql", "055_add_post_publish_immediately.sql",
            "060_track_external_publish_start.sql", "061_guard_legacy_publish_leases.sql",
            "067_isolate_scheduler_environments.sql", "068_central_dispatch_compatibility.sql",
            "069_post_content_revisions.sql", "070_campaign_drafts.sql",
            "071_campaign_names_and_media.sql", "072_plan_limits_and_atomic_catalog_quotas.sql",
            "074_f4e1_inert_campaign_reservations.sql",
        ]
        with cls.connect(autocommit=True) as con:
            for role in ("anon", "authenticated", "service_role"):
                assert con.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
            for name in names:
                con.execute((ROOT / "database/migrations" / name).read_text())
                if name == "036_add_profile_id_to_products_and_lists.sql":
                    source = (ROOT / "database/migrations/038_add_profile_id_to_remaining_tables.sql").read_text()
                    for table in ("posts", "schedulers"):
                        statement = (
                            "alter table public." + table
                            + " add column if not exists profile_id uuid references profiles(id) on delete set null;"
                        )
                        assert statement in source
                        con.execute(statement)
            con.execute(PROPOSAL.read_text())

    @classmethod
    def drop_disposable_database(cls):
        # Exact generated database only, never schema public or f4e_test.
        if re.fullmatch(r"f4e2b3_[0-9a-f]{32}", cls.database) is None:
            raise RuntimeError("Invalid disposable database name; refusing DROP")
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(cls.database)))

    def setUp(self):
        self.user, self.other_user = uuid.uuid4(), uuid.uuid4()
        self.profile, self.other_profile = uuid.uuid4(), uuid.uuid4()
        self.reservation, self.other_reservation = uuid.uuid4(), uuid.uuid4()
        self.occurrence = uuid.uuid4()
        with self.connect() as con:
            for user, profile in ((self.user, self.profile), (self.other_user, self.other_profile)):
                con.execute(
                    "INSERT INTO public.users(id,username,password) VALUES (%s,%s,'fixture-not-a-secret')",
                    (user, str(user)),
                )
                con.execute(
                    "INSERT INTO public.profiles(id,user_id,kind,nome) VALUES (%s,%s,'principal','fixture')",
                    (profile, user),
                )
            for reservation in (self.reservation, self.other_reservation):
                draft = con.execute(
                    """INSERT INTO public.campaign_drafts(user_id,profile_id,source_list_name,items)
                       VALUES (%s,%s,'fixture','[{"product_id":1}]') RETURNING id""",
                    (self.user, self.profile),
                ).fetchone()[0]
                con.execute(
                    """INSERT INTO public.campaign_reservations_f4e
                       (id,user_id,profile_id,draft_id,request_key,request_payload,draft_snapshot,media_snapshot)
                       VALUES (%s,%s,%s,%s,%s,'{"revision":1}','{}','[]')""",
                    (reservation, self.user, self.profile, draft, str(reservation)),
                )
            con.execute(
                """INSERT INTO public.campaign_occurrences_f4e(id,reservation_id,ordinal,planned_at)
                   VALUES (%s,%s,1,now()+interval '2 days')""",
                (self.occurrence, self.reservation),
            )
            self.post, self.schedule, self.job = self.new_dispatch(con)

    def new_dispatch(self, con, network="threads"):
        post = con.execute(
            "INSERT INTO public.posts(text,user_id,profile_id,network) VALUES ('fixture',%s,%s,%s) RETURNING id",
            (self.user, self.profile, network),
        ).fetchone()[0]
        schedule = con.execute(
            """INSERT INTO public.schedulers(post_id,user_id,profile_id,func,trigger,environment,dispatch_mode)
               VALUES (%s,%s,%s,%s,'date','staging','central') RETURNING id""",
            (post, self.user, self.profile, {"threads": "bot_post", "facebook": "bot_post_facebook"}[network]),
        ).fetchone()[0]
        job = con.execute(
            """INSERT INTO public.publish_jobs(scheduler_id,post_id,user_id,profile_id,network,idempotency_key)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
            (schedule, post, self.user, self.profile, network, str(uuid.uuid4())),
        ).fetchone()[0]
        return post, schedule, job

    def insert_link(self, con, **changes):
        data = dict(
            reservation_id=self.reservation, occurrence_id=self.occurrence,
            scheduler_id=self.schedule, publish_job_id=self.job, post_id=self.post,
            user_id=self.user, profile_id=self.profile,
            source_environment="staging", network="threads",
        )
        data.update(changes)
        return con.execute(
            sql.SQL("INSERT INTO public.campaign_dispatch_links_f4e ({}) VALUES ({}) RETURNING id").format(
                sql.SQL(",").join(map(sql.Identifier, data)),
                sql.SQL(",").join(sql.Placeholder() for _ in data),
            ),
            tuple(data.values()),
        ).fetchone()[0]

    def test_acl_rls_and_no_execution_permissions(self):
        with self.connect() as con:
            self.assertTrue(con.execute(
                "SELECT relrowsecurity FROM pg_class WHERE oid='public.campaign_dispatch_links_f4e'::regclass"
            ).fetchone()[0])
            for role in ("anon", "authenticated", "service_role"):
                for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    self.assertFalse(con.execute(
                        "SELECT has_table_privilege(%s,'public.campaign_dispatch_links_f4e',%s)",
                        (role, privilege),
                    ).fetchone()[0])
                self.assertFalse(con.execute(
                    "SELECT has_function_privilege(%s,'public.guard_campaign_dispatch_link_f4e()','EXECUTE')",
                    (role,),
                ).fetchone()[0])
            con.execute("SET LOCAL ROLE service_role")
            self.assertEqual(con.execute("SELECT count(*) FROM public.campaign_dispatch_links_f4e WHERE user_id=%s",
                                         (self.user,)).fetchone()[0], 0)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with con.transaction():
                    self.insert_link(con)

    def test_link_is_inert_and_immutable_even_for_owner(self):
        with self.connect() as con:
            link = self.insert_link(con)
            self.assertEqual(con.execute(
                "SELECT status,dispatch_enabled FROM public.campaign_dispatch_links_f4e WHERE id=%s", (link,)
            ).fetchone(), ("inert", False))
            for command in (
                "UPDATE public.campaign_dispatch_links_f4e SET dispatch_enabled=true WHERE id=%s",
                "UPDATE public.campaign_dispatch_links_f4e SET network='facebook' WHERE id=%s",
                "DELETE FROM public.campaign_dispatch_links_f4e WHERE id=%s",
            ):
                with self.subTest(command=command), self.assertRaises(psycopg.errors.CheckViolation):
                    with con.transaction():
                        con.execute(command, (link,))

    def test_cross_identity_or_initial_state_rolls_back(self):
        cases = (
            {"profile_id": self.other_profile}, {"user_id": self.other_user},
            {"reservation_id": self.other_reservation},
            {"source_environment": "production"}, {"network": "facebook"},
            {"publish_job_id": uuid.uuid4()},
        )
        with self.connect() as con:
            for changes in cases:
                with self.subTest(changes=changes), self.assertRaises(psycopg.Error):
                    with con.transaction():
                        self.insert_link(con, **changes)
            con.execute("UPDATE public.publish_jobs SET status='running' WHERE id=%s", (self.job,))
            with self.assertRaises(psycopg.errors.CheckViolation):
                with con.transaction():
                    self.insert_link(con)
            self.assertEqual(con.execute(
                "SELECT count(*) FROM public.campaign_dispatch_links_f4e WHERE user_id=%s", (self.user,)
            ).fetchone()[0], 0)

    def test_parent_identity_is_restricted_not_just_checked_at_insert(self):
        with self.connect() as con:
            self.insert_link(con)
            cases = (
                ("profiles", "user_id", self.other_user, self.profile),
                ("campaign_reservations_f4e", "profile_id", self.other_profile, self.reservation),
                ("campaign_occurrences_f4e", "reservation_id", self.other_reservation, self.occurrence),
                ("schedulers", "environment", "production", self.schedule),
                ("schedulers", "post_id", self.post + 1000000, self.schedule),
                ("posts", "network", "facebook", self.post),
                ("publish_jobs", "network", "facebook", self.job),
            )
            for table, column, value, identifier in cases:
                with self.subTest(table=table, column=column), self.assertRaises(psycopg.Error):
                    with con.transaction():
                        con.execute(
                            sql.SQL("UPDATE public.{} SET {}=%s WHERE id=%s").format(
                                sql.Identifier(table), sql.Identifier(column)), (value, identifier),
                        )
            for table, identifier in (("schedulers", self.schedule), ("posts", self.post),
                                      ("publish_jobs", self.job), ("profiles", self.profile)):
                with self.subTest(delete=table), self.assertRaises(psycopg.Error):
                    with con.transaction():
                        con.execute(sql.SQL("DELETE FROM public.{} WHERE id=%s").format(
                            sql.Identifier(table)), (identifier,))

    def test_lifecycle_and_unlinked_legacy_are_not_frozen(self):
        with self.connect() as con:
            self.insert_link(con)
            con.execute("UPDATE public.schedulers SET dispatch_cancelled_at=now(),dispatch_revision=2 WHERE id=%s",
                        (self.schedule,))
            con.execute("UPDATE public.publish_jobs SET status='failed',finished_at=now(),last_error='fixture' WHERE id=%s",
                        (self.job,))
            # Release RPC continua funcionando: identidade nao e estado.
            self.assertTrue(con.execute("SELECT public.release_campaign_f4e(%s,%s,%s)",
                                        (self.user, self.profile, self.reservation)).fetchone()[0])
            post, schedule, job = self.new_dispatch(con)
            con.execute("UPDATE public.schedulers SET environment='production' WHERE id=%s", (schedule,))
            con.execute("UPDATE public.posts SET network='facebook',text='editado' WHERE id=%s", (post,))
            con.execute("UPDATE public.publish_jobs SET network='facebook' WHERE id=%s", (job,))
            con.execute("DELETE FROM public.schedulers WHERE id=%s", (schedule,))
            self.assertIsNone(con.execute("SELECT id FROM public.publish_jobs WHERE id=%s", (job,)).fetchone())

    def test_unique_occurrence_network_and_job_without_reuse(self):
        with self.connect() as con:
            self.insert_link(con)
            with self.assertRaises(psycopg.errors.UniqueViolation):
                with con.transaction():
                    self.insert_link(con)
            other_occurrence = uuid.uuid4()
            con.execute(
                """INSERT INTO public.campaign_occurrences_f4e(id,reservation_id,ordinal,planned_at)
                   VALUES (%s,%s,2,now()+interval '3 days')""",
                (other_occurrence, self.reservation),
            )
            # Isola UNIQUE(publish_job_id), sem colidir occurrence+network.
            with self.assertRaises(psycopg.errors.UniqueViolation):
                with con.transaction():
                    self.insert_link(con, occurrence_id=other_occurrence)
            post, schedule, job = self.new_dispatch(con)
            with self.assertRaises(psycopg.errors.UniqueViolation):
                with con.transaction():
                    self.insert_link(con, post_id=post, scheduler_id=schedule, publish_job_id=job)
            post, schedule, job = self.new_dispatch(con, "facebook")
            self.insert_link(con, post_id=post, scheduler_id=schedule, publish_job_id=job, network="facebook")
            self.assertEqual(con.execute(
                "SELECT count(*) FROM public.campaign_dispatch_links_f4e WHERE occurrence_id=%s", (self.occurrence,)
            ).fetchone()[0], 2)

    def test_uncommitted_link_blocks_parent_change_then_restricts_it(self):
        with self.connect() as writer:
            self.insert_link(writer)
            with self.connect() as other:
                other.execute("SET LOCAL lock_timeout='100ms'")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    with other.transaction():
                        other.execute("UPDATE public.schedulers SET environment='production' WHERE id=%s",
                                      (self.schedule,))
            writer.commit()
        with self.connect() as other:
            with self.assertRaises(psycopg.errors.ForeignKeyViolation):
                other.execute("UPDATE public.schedulers SET environment='production' WHERE id=%s", (self.schedule,))

    def test_old_repeatable_read_snapshot_cannot_rewrite_parent_identity(self):
        with self.connect() as old:
            old.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            old.execute("SELECT count(*) FROM public.campaign_dispatch_links_f4e").fetchone()
            with self.connect() as writer:
                self.insert_link(writer)
            with self.assertRaises((psycopg.errors.ForeignKeyViolation, psycopg.errors.SerializationFailure)):
                old.execute("UPDATE public.schedulers SET environment='production' WHERE id=%s", (self.schedule,))

    def test_reapply_is_rejected_and_rolls_back_without_erasing_links(self):
        with self.connect() as con:
            link = self.insert_link(con)
        with self.connect(autocommit=True) as con:
            with self.assertRaises(psycopg.errors.DuplicateTable):
                try:
                    con.execute(PROPOSAL.read_text())
                finally:
                    con.execute("ROLLBACK")
            self.assertIsNotNone(con.execute(
                "SELECT id FROM public.campaign_dispatch_links_f4e WHERE id=%s", (link,)
            ).fetchone())


    def test_cron_claim_timestamp_is_complete_in_real_postgres(self):
        """Regressao do InvalidDatetimeFormat: slot HH:MM nao pode perder minutos."""
        from datetime import datetime

        source = (ROOT / "database/publish_jobs.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("right(job.idempotency_key, 16)"), 3)
        self.assertNotIn("split_part(job.idempotency_key, ':', 2)", source)
        key = str(self.schedule) + ":2026-11-03T15:47"
        with self.connect() as con:
            value = con.execute(
                """SELECT CASE WHEN %s ~ ':[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}
    unittest.main()

                         THEN right(%s, 16)::timestamp ELSE NULL END""",
                (key, key),
            ).fetchone()[0]
            invalid = con.execute(
                """SELECT CASE WHEN %s ~ ':[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}
    unittest.main()

                         THEN right(%s, 16)::timestamp ELSE NULL END""",
                ("legacy-manual-retry", "legacy-manual-retry"),
            ).fetchone()[0]
        self.assertEqual(value, datetime(2026, 11, 3, 15, 47))
        self.assertIsNone(invalid)


if __name__ == "__main__":
    unittest.main()

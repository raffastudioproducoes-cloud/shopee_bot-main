"""Limpeza de posts de campanha (097) em PostgreSQL descartável. Sem chamadas a redes sociais."""
import psycopg

from tests.sql.test_f4e2b6_postgres import TestCampaignRuntime, ROOT


class TestCampaignPostPurge(TestCampaignRuntime):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.connect(autocommit=True) as con:
            # No banco real estas chaves já são ON DELETE CASCADE (migrations 017/053); o fixture
            # simplificado não as declara, então reproduzimos a regra de produção aqui.
            for table, constraint, column, parent in (
                ("schedulers", "schedulers_post_id_fkey", "post_id", "posts"),
                ("publish_jobs", "publish_jobs_post_id_fkey", "post_id", "posts"),
                ("publish_jobs", "publish_jobs_scheduler_id_fkey", "scheduler_id", "schedulers"),
            ):
                con.execute(f"ALTER TABLE public.{table} DROP CONSTRAINT IF EXISTS {constraint}")
                con.execute(
                    f"ALTER TABLE public.{table} ADD CONSTRAINT {constraint} "
                    f"FOREIGN KEY ({column}) REFERENCES public.{parent}(id) ON DELETE CASCADE"
                )
            con.execute((ROOT / "097_campaign_post_purge.sql").read_text())

    def _post_of(self, rid):
        with self.connect() as con:
            return con.execute(
                "SELECT post_id FROM campaign_network_slots_f4e WHERE reservation_id=%s", (rid,)
            ).fetchone()[0]

    def _purge(self, post_ids):
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            return con.execute(
                "SELECT public.purge_campaign_posts_f4e(%s,%s,%s)", (self.user, self.profile, post_ids)
            ).fetchone()[0]

    def test_trigger_blocks_plain_delete_but_purge_removes_post_slot_and_job(self):
        rid, _ = self.materialize()
        post = self._post_of(rid)
        with self.assertRaises(psycopg.Error) as ctx:
            with self.connect() as con:
                con.execute("DELETE FROM posts WHERE id=%s", (post,))
        self.assertIn("campaign_job_immutable", str(ctx.exception))
        self.assertEqual(self._purge([post]), 1)
        with self.connect() as con:
            for table, column in (("posts", "id"), ("schedulers", "post_id"), ("publish_jobs", "post_id"),
                                   ("campaign_network_slots_f4e", "post_id")):
                self.assertEqual(con.execute(
                    f"SELECT count(*) FROM {table} WHERE {column}=%s", (post,)).fetchone()[0], 0, table)
            self.assertEqual(con.execute(
                "SELECT count(*) FROM campaign_reservations_f4e WHERE id=%s", (rid,)).fetchone()[0], 1)

    def test_running_slot_is_refused_and_nothing_is_deleted(self):
        rid, _ = self.materialize()
        post = self._post_of(rid)
        with self.connect() as con:
            con.execute("ALTER TABLE campaign_network_slots_f4e DISABLE TRIGGER trg_guard_campaign_network_slot_f4e")
            con.execute("UPDATE campaign_network_slots_f4e SET state='running' WHERE reservation_id=%s", (rid,))
            con.execute("ALTER TABLE campaign_network_slots_f4e ENABLE TRIGGER trg_guard_campaign_network_slot_f4e")
        with self.assertRaises(psycopg.Error) as ctx:
            self._purge([post])
        self.assertIn("campaign_post_running", str(ctx.exception))
        with self.connect() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM posts WHERE id=%s", (post,)).fetchone()[0], 1)

    def test_executed_slot_stays_as_history(self):
        rid, _ = self.materialize()
        post = self._post_of(rid)
        with self.connect() as con:
            con.execute("ALTER TABLE campaign_network_slots_f4e DISABLE TRIGGER trg_guard_campaign_network_slot_f4e")
            con.execute("UPDATE campaign_network_slots_f4e SET state='succeeded' WHERE reservation_id=%s", (rid,))
            con.execute("ALTER TABLE campaign_network_slots_f4e ENABLE TRIGGER trg_guard_campaign_network_slot_f4e")
        with self.assertRaises(psycopg.Error) as ctx:
            self._purge([post])
        self.assertIn("campaign_post_has_history", str(ctx.exception))

    def test_other_users_post_is_never_deleted(self):
        rid, _ = self.materialize()
        post = self._post_of(rid)
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            deleted = con.execute(
                "SELECT public.purge_campaign_posts_f4e(%s,%s,%s)",
                (self.profile, self.user, [post]),  # dono/perfil invertidos
            ).fetchone()[0]
        self.assertEqual(deleted, 0)
        with self.connect() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM posts WHERE id=%s", (post,)).fetchone()[0], 1)

    def test_cancel_then_purge_removes_posts_keeps_reservation_and_history_rows(self):
        rid, _ = self.materialize()
        post = self._post_of(rid)
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            with self.assertRaises(psycopg.Error) as ctx:
                with con.transaction():
                    con.execute("SELECT public.purge_cancelled_campaign_f4e(%s,%s,%s)",
                                (self.user, self.profile, rid))
            self.assertIn("campaign_not_cancelled", str(ctx.exception))
            con.execute("SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,'cancel')",
                        (self.user, self.profile, rid))
            self.assertEqual(con.execute("SELECT public.purge_cancelled_campaign_f4e(%s,%s,%s)",
                                         (self.user, self.profile, rid)).fetchone()[0], 1)
            con.execute("RESET ROLE")
            self.assertEqual(con.execute("SELECT count(*) FROM posts WHERE id=%s", (post,)).fetchone()[0], 0)
            self.assertEqual(con.execute(
                "SELECT lifecycle,status FROM campaign_reservations_f4e WHERE id=%s", (rid,)).fetchone(),
                ("cancelled", "released"))

    def test_public_roles_cannot_call_purge(self):
        with self.connect() as con:
            for role in ("anon", "authenticated"):
                for fn in ("public.purge_campaign_posts_f4e(uuid,uuid,integer[])",
                           "public.purge_cancelled_campaign_f4e(uuid,uuid,uuid)"):
                    self.assertFalse(con.execute(
                        "SELECT has_function_privilege(%s,%s,'EXECUTE')", (role, fn)).fetchone()[0])

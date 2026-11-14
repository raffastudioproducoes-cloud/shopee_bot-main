"""Migração 102 (livro de consumo de cota) SOMENTE em PostgreSQL descartável da CI.

Banco próprio criado e apagado pelo teste, migrations reais de 001 a 073 + 102,
privilégios padrão iguais aos do Supabase (ALL para anon/authenticated/service_role)
para provar que os REVOKE/GRANT da 102 fecham o livro. Nunca acessa Supabase.
"""
import os
import re
import unittest
import uuid
from pathlib import Path

import psycopg
from psycopg import sql

DSN = "postgresql://postgres:postgres@127.0.0.1:5432/f4e_test"
ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = (
    "001_create_users_table.sql", "002_create_products_table.sql",
    "003_create_product_lists_table.sql", "012_create_posts_table.sql",
    "017_create_schedulers_table.sql", "023_add_network_to_posts.sql",
    "035_create_profiles_table.sql", "036_add_profile_id_to_products_and_lists.sql",
    "044_add_group_id_to_posts.sql", "047_add_scheduler_days_of_week.sql",
    "053_create_publish_jobs.sql", "055_add_post_publish_immediately.sql",
    "060_track_external_publish_start.sql", "061_guard_legacy_publish_leases.sql",
    "067_isolate_scheduler_environments.sql", "068_central_dispatch_compatibility.sql",
    "072_plan_limits_and_atomic_catalog_quotas.sql", "073_post_publication_plan_quotas.sql",
    "102_quota_ledger.sql",
)
RESERVE = "SELECT public.reserve_post_plan_quota(%s,%s,%s,%s,%s::smallint[],%s::time[])"


class TestQuotaLedger102Postgres(unittest.TestCase):
    @classmethod
    def connect(cls, **kwargs):
        return psycopg.connect(DSN, dbname=cls.database, **kwargs)

    @classmethod
    def setUpClass(cls):
        if os.getenv("F4E_DISPOSABLE_DSN") != DSN:
            raise unittest.SkipTest("Somente banco descartável de CI")
        cls.database = "ledger102_" + uuid.uuid4().hex
        with psycopg.connect(DSN, autocommit=True) as con:
            for role, extra in (("anon", ""), ("authenticated", ""), ("service_role", " BYPASSRLS")):
                if not con.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                    con.execute(f"CREATE ROLE {role} NOLOGIN{extra}")
            con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database)))
        cls.addClassCleanup(cls.drop_disposable_database)
        with cls.connect(autocommit=True) as con:
            con.execute("GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role")
            for kind in ("TABLES", "SEQUENCES", "FUNCTIONS"):
                verb = "EXECUTE" if kind == "FUNCTIONS" else "ALL"
                con.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT {verb} ON {kind} "
                            "TO anon, authenticated, service_role")
            for name in MIGRATIONS:
                con.execute((ROOT / "database/migrations" / name).read_text(encoding="utf-8"))
                if name == "036_add_profile_id_to_products_and_lists.sql":
                    for table in ("posts", "schedulers"):
                        con.execute(f"ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS profile_id uuid "
                                    "REFERENCES profiles(id) ON DELETE SET NULL")
            # Idempotente: reaplicar não duplica corte, trigger nem policy.
            con.execute((ROOT / "database/migrations/102_quota_ledger.sql").read_text(encoding="utf-8"))

    @classmethod
    def drop_disposable_database(cls):
        if re.fullmatch(r"ledger102_[0-9a-f]{32}", cls.database) is None:
            raise RuntimeError("Nome de banco descartável inválido; DROP recusado")
        with psycopg.connect(DSN, autocommit=True) as con:
            con.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(cls.database)))

    # ---------- fixtures ----------
    def account(self, con, tier="free", access="USER"):
        user, profile = uuid.uuid4(), uuid.uuid4()
        con.execute("INSERT INTO public.users(id,username,password,access,plan_tier) "
                    "VALUES (%s,%s,'fixture-not-a-secret',%s,%s)", (user, str(user), access, tier))
        con.execute("INSERT INTO public.profiles(id,user_id,kind,nome) VALUES (%s,%s,'principal','fixture')",
                    (profile, user))
        return user, profile

    def post(self, con, user, profile, immediate=False):
        return con.execute("INSERT INTO public.posts(text,user_id,profile_id,network,publish_immediately) "
                           "VALUES ('fixture',%s,%s,'threads',%s) RETURNING id",
                           (user, profile, immediate)).fetchone()[0]

    def as_service(self, con, query, params=()):
        # SET ROLE dentro do savepoint: se a função falhar, o rollback desfaz o papel.
        with con.transaction():
            con.execute("SET ROLE service_role")
            row = con.execute(query, params).fetchone()
            con.execute("RESET ROLE")
        return row[0] if row else None

    def reserve(self, con, user, profile, post, kind, days=(), times=()):
        return self.as_service(con, RESERVE, (user, profile, post, kind, list(days), list(times)))

    def release(self, con, user, profile, post):
        return self.as_service(con, "SELECT public.release_failed_post_plan_quota(%s,%s,%s)",
                               (user, profile, post))

    def assert_blocked(self, con, code, *args, **kwargs):
        with self.assertRaises(psycopg.errors.RaiseException) as raised:
            self.reserve(con, *args, **kwargs)
        self.assertIn(code, str(raised.exception))

    def delete_post(self, con, post):
        self.as_service(con, "DELETE FROM public.posts WHERE id=%s RETURNING id", (post,))

    def ledger(self, con, user, kind):
        return con.execute("SELECT coalesce(sum(amount),0) FROM public.quota_ledger WHERE user_id=%s AND kind=%s",
                           (user, kind)).fetchone()[0]

    # ---------- (a) apagar post não devolve cota ----------
    def test_deleting_recurring_post_does_not_return_daily_quota(self):
        with self.connect() as con:
            user, profile = self.account(con)  # Free: 1 horário/dia
            first = self.post(con, user, profile)
            self.reserve(con, user, profile, first, "recurring", [1], ["09:00"])
            self.delete_post(con, first)
            self.assertEqual(self.ledger(con, user, "recurring"), 1)
            self.assertEqual(self.ledger(con, user, "recurring_released"), 1)
            second = self.post(con, user, profile)
            self.assert_blocked(con, "plan_recurring_quota_exceeded",
                                user, profile, second, "recurring", [1], ["15:00"])
            # Só o dia da semana do horário apagado fica ocupado.
            self.reserve(con, user, profile, second, "recurring", [2], ["15:00"])
            # 24 h depois da exclusão o dia já passou: manutenção explícita simula o tempo.
            con.execute("ALTER TABLE public.quota_ledger DISABLE TRIGGER trg_quota_ledger_immutable")
            con.execute("UPDATE public.quota_ledger SET created_at=now()-interval '25 hours' "
                        "WHERE user_id=%s AND kind='recurring_released'", (user,))
            con.execute("ALTER TABLE public.quota_ledger ENABLE TRIGGER trg_quota_ledger_immutable")
            third = self.post(con, user, profile)
            self.reserve(con, user, profile, third, "recurring", [1], ["15:00"])

    def test_deleting_immediate_post_and_its_reservation_does_not_return_hourly_quota(self):
        with self.connect() as con:
            user, profile = self.account(con)  # Free: 1 imediata/hora
            first = self.post(con, user, profile, immediate=True)
            self.reserve(con, user, profile, first, "immediate")
            self.delete_post(con, first)
            con.execute("DELETE FROM public.plan_immediate_dispatches WHERE user_id=%s", (user,))
            second = self.post(con, user, profile, immediate=True)
            self.assert_blocked(con, "plan_immediate_quota_exceeded", user, profile, second, "immediate")

    def test_failed_creation_compensates_once_and_only_without_schedule(self):
        with self.connect() as con:
            user, profile = self.account(con)
            post = self.post(con, user, profile, immediate=True)
            self.reserve(con, user, profile, post, "immediate")
            released = self.release(con, user, profile, post)
            again = self.release(con, user, profile, post)
            self.assertEqual((released, again), (1, 0))
            self.assertEqual(self.ledger(con, user, "immediate"), 0)
            self.reserve(con, user, profile, self.post(con, user, profile, True), "immediate")

            recurring = self.post(con, user, profile)
            self.reserve(con, user, profile, recurring, "recurring", [3], ["08:00"])
            self.assertEqual(self.release(con, user, profile, recurring), 1)
            self.delete_post(con, recurring)
            self.assertEqual(self.ledger(con, user, "recurring_released"), 0)
            self.reserve(con, user, profile, self.post(con, user, profile), "recurring", [3], ["09:00"])

            scheduled = self.post(con, user, profile)
            self.reserve(con, user, profile, scheduled, "recurring", [4], ["08:00"])
            con.execute("INSERT INTO public.schedulers(post_id,user_id,profile_id,func,trigger,time,days_of_week,"
                        "environment) VALUES (%s,%s,%s,'bot_post','cron','08:00',ARRAY[4]::smallint[],'staging')",
                        (scheduled, user, profile))
            self.assertEqual(self.release(con, user, profile, scheduled), 0)

    # ---------- (b) livro imutável e fechado ----------
    def test_ledger_rejects_update_delete_truncate_and_direct_writes(self):
        with self.connect() as con:
            user, profile = self.account(con)
            self.reserve(con, user, profile, self.post(con, user, profile, True), "immediate")
            for statement in ("UPDATE public.quota_ledger SET amount=-5",
                              "DELETE FROM public.quota_ledger",
                              "TRUNCATE public.quota_ledger",
                              "UPDATE public.quota_ledger_cutover SET cutover_at=now()"):
                with self.subTest(owner=statement), self.assertRaises(psycopg.errors.RaiseException) as raised:
                    with con.transaction():
                        con.execute(statement)
                self.assertIn("quota_ledger_immutable", str(raised.exception))
            for role in ("service_role", "anon", "authenticated"):
                for statement in ("UPDATE public.quota_ledger SET amount=-5",
                                  "DELETE FROM public.quota_ledger",
                                  "INSERT INTO public.quota_ledger(user_id,kind,amount) "
                                  f"VALUES ('{user}','immediate',-5)"):
                    with self.subTest(role=role, statement=statement):
                        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                            with con.transaction():
                                con.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                                con.execute(statement)
            for role in ("anon", "authenticated"):
                self.assertFalse(con.execute("SELECT has_table_privilege(%s,'public.quota_ledger','SELECT')",
                                             (role,)).fetchone()[0])
                self.assertFalse(con.execute(
                    "SELECT has_function_privilege(%s,'public.record_quota_use(uuid,uuid,text,text,integer,"
                    "uuid,integer,text,smallint,time)','EXECUTE')", (role,)).fetchone()[0])
            with self.assertRaises(psycopg.errors.RaiseException) as raised:
                with con.transaction():
                    con.execute("SET LOCAL ROLE service_role")
                    con.execute("SELECT public.record_quota_use(%s,%s,'immediate',NULL,NULL,NULL,-1)",
                                (user, profile))
            self.assertIn("invalid_quota_amount", str(raised.exception))
            self.assertEqual(con.execute("SELECT count(*) FROM public.quota_ledger_cutover").fetchone()[0], 1)
            self.assertTrue(con.execute("SELECT relrowsecurity FROM pg_class "
                                        "WHERE oid='public.quota_ledger'::regclass").fetchone()[0])

    # ---------- (c) isolamento entre contas ----------
    def test_account_a_does_not_consume_account_b(self):
        with self.connect() as con:
            a_user, a_profile = self.account(con)
            b_user, b_profile = self.account(con)
            a_post = self.post(con, a_user, a_profile, True)
            self.reserve(con, a_user, a_profile, a_post, "immediate")
            self.assert_blocked(con, "plan_immediate_quota_exceeded",
                                a_user, a_profile, self.post(con, a_user, a_profile, True), "immediate")
            self.reserve(con, b_user, b_profile, self.post(con, b_user, b_profile, True), "immediate")
            a_rec = self.post(con, a_user, a_profile)
            self.reserve(con, a_user, a_profile, a_rec, "recurring", [5], ["10:00"])
            self.delete_post(con, a_rec)
            self.reserve(con, b_user, b_profile, self.post(con, b_user, b_profile), "recurring", [5], ["10:00"])
            self.assert_blocked(con, "profile_not_owned",
                                a_user, b_profile, self.post(con, b_user, b_profile, True), "immediate")
            self.assertEqual(self.ledger(con, b_user, "immediate"), 1)

    # ---------- (d) limites de Free/Pro/Premium ----------
    def test_plan_limits_still_apply_without_double_counting(self):
        with self.connect() as con:
            free_user, free_profile = self.account(con, "free")
            self.assert_blocked(con, "plan_recurring_quota_exceeded", free_user, free_profile,
                                self.post(con, free_user, free_profile), "recurring", [0], ["08:00", "09:00"])
            pro_user, pro_profile = self.account(con, "pro")
            remaining = [self.reserve(con, pro_user, pro_profile, self.post(con, pro_user, pro_profile, True),
                                      "immediate") for _ in range(3)]
            self.assertEqual(remaining, [2, 1, 0])
            self.assert_blocked(con, "plan_immediate_quota_exceeded", pro_user, pro_profile,
                                self.post(con, pro_user, pro_profile, True), "immediate")
            premium_user, premium_profile = self.account(con, "premium")
            self.reserve(con, premium_user, premium_profile, self.post(con, premium_user, premium_profile),
                         "recurring", [6], ["08:00", "09:00", "10:00", "11:00", "12:00"])
            self.assert_blocked(con, "plan_recurring_quota_exceeded", premium_user, premium_profile,
                                self.post(con, premium_user, premium_profile), "recurring", [6], ["13:00"])

    def test_reservations_before_cutover_still_count(self):
        with self.connect() as con:
            user, profile = self.account(con)
            old = self.post(con, user, profile, True)
            con.execute("INSERT INTO public.plan_immediate_dispatches(user_id,profile_id,post_id,created_at) "
                        "SELECT %s,%s,%s,cutover_at-interval '1 minute' FROM public.quota_ledger_cutover",
                        (user, profile, old))
            self.assert_blocked(con, "plan_immediate_quota_exceeded",
                                user, profile, self.post(con, user, profile, True), "immediate")

    # ---------- (e) ADMIN isento ----------
    def test_admin_is_exempt_and_not_recorded(self):
        with self.connect() as con:
            user, profile = self.account(con, "free", "ADMIN")
            for _ in range(3):
                self.assertEqual(self.reserve(con, user, profile, self.post(con, user, profile, True),
                                              "immediate"), 0)
            self.assertEqual(con.execute("SELECT count(*) FROM public.quota_ledger WHERE user_id=%s",
                                         (user,)).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

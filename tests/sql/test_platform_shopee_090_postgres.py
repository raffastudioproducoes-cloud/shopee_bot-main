"""SQL 090 apenas no PostgreSQL 16 descartável da CI, nunca Supabase real."""

import os
import unittest
import uuid
from pathlib import Path

import psycopg


DSN = "postgresql://postgres:postgres@127.0.0.1:5432/f4e_test"
ROOT = Path(__file__).resolve().parents[2]


class TestPlatformShopee090Postgres(unittest.TestCase):
    def test_idempotence_backfill_and_rls(self):
        if os.getenv("F4E_DISPOSABLE_DSN") != DSN:
            self.skipTest("Somente banco descartável de CI")
        admin, user = uuid.uuid4(), uuid.uuid4()
        migration = (ROOT / "database/migrations/090_platform_shopee_affiliate_ids.sql").read_text(encoding="utf-8")
        with psycopg.connect(DSN) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS public.shopee_credentials (
                id serial PRIMARY KEY, user_id uuid REFERENCES public.users(id), app_id text,
                secret text, status boolean, updated_at timestamp
            )""")
            con.execute("INSERT INTO public.users(id, access, plan_tier) VALUES (%s, 'ADMIN', 'pro'), (%s, 'USER', 'pro')",
                        (admin, user))
            con.execute("""INSERT INTO public.shopee_credentials(user_id, app_id, secret, status, updated_at)
                VALUES (%s, 'admin-app', 'cipher-admin', true, now()),
                       (%s, 'user-app', 'cipher-user', true, now())""", (admin, user))
            con.execute(migration)
            con.execute(migration)
            rows = con.execute("""SELECT environment, app_id, secret FROM public.platform_shopee_credentials
                ORDER BY environment""").fetchall()
            self.assertEqual(rows, [
                ("production", "admin-app", "cipher-admin"),
                ("staging", "admin-app", "cipher-admin"),
            ])
            for table in ("platform_shopee_credentials", "shopee_affiliate_accounts"):
                enabled = con.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass",
                                      (f"public.{table}",)).fetchone()[0]
                self.assertTrue(enabled)
                for role in ("anon", "authenticated"):
                    allowed = con.execute("SELECT has_table_privilege(%s, %s, 'SELECT')",
                                          (role, f"public.{table}")).fetchone()[0]
                    self.assertFalse(allowed)
            con.execute("INSERT INTO public.shopee_affiliate_accounts(user_id, affiliate_id) VALUES (%s, '12345678900')", (user,))
            with self.assertRaises(psycopg.errors.CheckViolation):
                with con.transaction():
                    con.execute("UPDATE public.shopee_affiliate_accounts SET affiliate_id='bad' WHERE user_id=%s", (user,))
            # DDL e fixture de teste não persistem na base descartável.
            con.rollback()

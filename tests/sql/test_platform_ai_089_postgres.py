"""SQL 089 against the existing disposable PostgreSQL 16 CI service ONLY."""
import os
import unittest
import uuid
from pathlib import Path

import psycopg

DSN = "postgresql://postgres:postgres@127.0.0.1:5432/f4e_test"
ROOT = Path(__file__).resolve().parents[2]


class TestPlatformAi089Postgres(unittest.TestCase):
    def test_migration_is_idempotent_private_and_copies_admin_ciphertext(self):
        if os.getenv("F4E_DISPOSABLE_DSN") != DSN:
            self.skipTest("Somente Postgres descartável da CI; nunca contra Supabase real")
        admin, customer = uuid.uuid4(), uuid.uuid4()
        migration = (ROOT / "database/migrations/089_platform_ai_credentials.sql").read_text(encoding="utf-8")
        with psycopg.connect(DSN) as con:
            # F4E fixtures in the preceding CI jobs already create users/roles.
            con.execute("""
                CREATE TABLE IF NOT EXISTS public.ai_credentials (
                    id serial PRIMARY KEY, user_id uuid NOT NULL REFERENCES public.users(id),
                    provider text NOT NULL, secret text, model text, status boolean,
                    updated_at timestamptz
                )
            """)
            con.execute("INSERT INTO public.users (id, access, plan_tier) VALUES (%s, 'ADMIN', 'pro'), (%s, 'USER', 'pro')",
                        (admin, customer))
            con.execute("""
                INSERT INTO public.ai_credentials(user_id, provider, secret, model, status, updated_at)
                VALUES (%s, 'gemini', 'encrypted-admin-secret', 'gemini-test', true, now()),
                       (%s, 'openai', 'encrypted-user-secret', 'model-user', true, now())
            """, (admin, customer))
            con.execute(migration)
            con.execute(migration)  # rerun must not fail or create duplicates
            rows = con.execute("""
                SELECT environment, provider, secret, status FROM public.platform_ai_credentials
                ORDER BY environment
            """).fetchall()
            self.assertEqual(rows, [
                ("production", "gemini", "encrypted-admin-secret", True),
                ("staging", "gemini", "encrypted-admin-secret", True),
            ])
            settings = con.execute("SELECT environment, active_provider FROM public.platform_ai_settings ORDER BY environment").fetchall()
            self.assertEqual(settings, [("production", "gemini"), ("staging", "gemini")])
            for table in ("platform_ai_credentials", "platform_ai_settings"):
                enabled = con.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass", (f"public.{table}",)).fetchone()[0]
                self.assertTrue(enabled)
                for role in ("anon", "authenticated"):
                    allowed = con.execute("SELECT has_table_privilege(%s, %s, 'SELECT')", (role, f"public.{table}")).fetchone()[0]
                    self.assertFalse(allowed)
            # Intentionally roll back fixture/DDL. This suite never writes live data.
            con.rollback()

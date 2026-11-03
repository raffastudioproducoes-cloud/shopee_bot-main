"""Runtime F4E tests on disposable PostgreSQL only. No social API calls."""
import uuid
from datetime import datetime,timezone,timedelta

from tests.sql.test_f4e2b5_postgres import TestCampaignNetworkReservations, ROOT


class TestCampaignRuntime(TestCampaignNetworkReservations):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.connect(autocommit=True) as con:
            con.execute("""
                CREATE TYPE public.mediatype AS ENUM ('IMAGE','VIDEO');
                CREATE TABLE public.medias (
                  id serial PRIMARY KEY,file_name text,file_path text,size integer,
                  type public.mediatype,user_id uuid,profile_id uuid
                );
                CREATE TABLE public.posts_products (post_id integer,product_id integer,display_order integer);
                CREATE TABLE public.posts_medias (post_id integer,media_id integer,display_order integer);
                CREATE SEQUENCE public.posts_id_seq START 10000;
                ALTER TABLE public.posts ALTER COLUMN id SET DEFAULT nextval('public.posts_id_seq');
                ALTER TABLE public.posts ADD COLUMN text text;
                ALTER TABLE public.posts ADD COLUMN profile_id uuid;
                ALTER TABLE public.posts ADD COLUMN network text DEFAULT 'threads';
                ALTER TABLE public.posts ADD COLUMN publish_immediately boolean DEFAULT false;
                ALTER TABLE public.schedulers ADD COLUMN func text;
                ALTER TABLE public.schedulers ADD COLUMN trigger text;
                ALTER TABLE public.schedulers ADD COLUMN run_date timestamp;
                ALTER TABLE public.schedulers ADD COLUMN user_id uuid;
                ALTER TABLE public.schedulers ADD COLUMN profile_id uuid;
                ALTER TABLE public.schedulers ADD COLUMN environment text DEFAULT 'production';
                ALTER TABLE public.schedulers ADD COLUMN dispatch_mode text DEFAULT 'legacy';
                ALTER TABLE public.schedulers ADD COLUMN dispatch_cancelled_at timestamptz;
                ALTER TABLE public.publish_jobs ADD COLUMN post_id integer;
                ALTER TABLE public.publish_jobs ADD COLUMN user_id uuid;
                ALTER TABLE public.publish_jobs ADD COLUMN profile_id uuid;
                ALTER TABLE public.publish_jobs ADD COLUMN network text;
                ALTER TABLE public.publish_jobs ADD COLUMN idempotency_key text UNIQUE;
                ALTER TABLE public.publish_jobs ADD COLUMN status text NOT NULL DEFAULT 'pending';
                ALTER TABLE public.publish_jobs ADD COLUMN attempt integer DEFAULT 0;
                ALTER TABLE public.publish_jobs ADD COLUMN claim_token uuid;
                ALTER TABLE public.publish_jobs ADD COLUMN preflight_claim_token uuid;
                ALTER TABLE public.publish_jobs ADD COLUMN external_started_at timestamptz;
                ALTER TABLE public.publish_jobs ADD COLUMN locked_by text;
                ALTER TABLE public.publish_jobs ADD COLUMN locked_at timestamptz;
                ALTER TABLE public.publish_jobs ADD COLUMN started_at timestamptz;
                ALTER TABLE public.publish_jobs ADD COLUMN finished_at timestamptz;
                ALTER TABLE public.publish_jobs ADD COLUMN external_id text;
                ALTER TABLE public.publish_jobs ADD COLUMN last_error text;
                ALTER TABLE public.publish_jobs ADD COLUMN scheduled_for timestamptz;
            """)
            for migration in (
                '075_campaign_publication_origin_guards.sql',
                '077_campaign_materialization.sql',
                '078_campaign_executor.sql',
            ):
                con.execute((ROOT / migration).read_text())

    def test_activate_pause_resume_cancel_and_history(self):
        # V1 entrypoint has been revoked for service_role by migration 077.
        with self.connect() as con:
            self.assertFalse(con.execute("""
                SELECT has_function_privilege('service_role',
                  'public.activate_campaign_networks_f4e(uuid,uuid,uuid,text)','EXECUTE')
            """).fetchone()[0])

    def materialize(self):
        rid = self.reserve(draft_index=1)
        with self.connect() as con:
            con.execute("INSERT INTO public.campaign_oauth_checks_f4e(reservation_id,network) VALUES (%s,'threads')",(rid,))
            con.execute("SET LOCAL ROLE service_role")
            count = con.execute(
                "SELECT public.materialize_campaign_f4e(%s,%s,%s,'staging')",
                (self.user,self.profile,rid),
            ).fetchone()[0]
        return rid,count

    def test_post_scheduler_job_campaign_origin_and_idempotency(self):
        rid,count = self.materialize()
        self.assertEqual(count,1)
        with self.connect() as con:
            rows = con.execute("""
                SELECT p.text,p.network,s.environment,s.publication_origin,
                       j.publication_origin,j.status,n.state
                FROM campaign_network_slots_f4e n
                JOIN posts p ON p.id=n.post_id
                JOIN schedulers s ON s.id=n.scheduler_id
                JOIN publish_jobs j ON j.id=n.publish_job_id
                WHERE n.reservation_id=%s
            """,(rid,)).fetchall()
            self.assertEqual(rows,[("A","threads","staging","campaign","campaign","pending","planned")])
            con.execute("SET LOCAL ROLE service_role")
            self.assertEqual(con.execute(
                "SELECT public.materialize_campaign_f4e(%s,%s,%s,'staging')",
                (self.user,self.profile,rid),
            ).fetchone()[0],1)
            self.assertEqual(con.execute(
                "SELECT count(*) FROM posts WHERE user_id=%s",(self.user,),
            ).fetchone()[0],1)

    def _due(self,rid):
        # A disposable fixture simulates the clock transition without waiting 30 minutes.
        with self.connect() as con:
            con.execute("ALTER TABLE campaign_network_slots_f4e DISABLE TRIGGER trg_guard_campaign_network_slot_f4e")
            due=datetime.now(timezone.utc)-timedelta(minutes=10)
            con.execute("UPDATE campaign_occurrences_f4e SET planned_at=%s WHERE reservation_id=%s",(due,rid))
            con.execute("UPDATE campaign_network_slots_f4e SET planned_at=%s WHERE reservation_id=%s",(due,rid))
            con.execute("ALTER TABLE campaign_network_slots_f4e ENABLE TRIGGER trg_guard_campaign_network_slot_f4e")

    def test_claim_pause_blocks_external_and_allows_terminal_record(self):
        rid,_=self.materialize()
        self._due(rid)
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            claim=con.execute(
                "SELECT public.claim_campaign_publication_f4e('staging','test-worker')"
            ).fetchone()[0]
            self.assertIsNotNone(claim)
            self.assertEqual(claim["network"],"threads")
            self.assertEqual(con.execute(
                "SELECT public.change_campaign_lifecycle_f4e(%s,%s,%s,'pause')",
                (self.user,self.profile,rid),
            ).fetchone()[0],"paused")
            self.assertFalse(con.execute(
                "SELECT public.mark_campaign_external_f4e('staging',%s,%s)",
                (claim["publish_job_id"],claim["claim_token"]),
            ).fetchone()[0])
            self.assertTrue(con.execute(
                "SELECT public.finish_campaign_publication_f4e('staging',%s,%s,'failed',NULL,'cancelado antes do envio')",
                (claim["publish_job_id"],claim["claim_token"]),
            ).fetchone()[0])
            self.assertEqual(con.execute(
                "SELECT state FROM campaign_network_slots_f4e WHERE reservation_id=%s",(rid,)
            ).fetchone()[0],"failed")

    def test_claim_idempotent_under_single_slot(self):
        rid,_=self.materialize()
        self._due(rid)
        with self.connect() as con:
            con.execute("SET LOCAL ROLE service_role")
            first=con.execute("SELECT public.claim_campaign_publication_f4e('staging','worker-a')").fetchone()[0]
            second=con.execute("SELECT public.claim_campaign_publication_f4e('staging','worker-b')").fetchone()[0]
            self.assertIsNotNone(first)
            self.assertIsNone(second)
            self.assertTrue(con.execute(
                "SELECT public.mark_campaign_external_f4e('staging',%s,%s)",
                (first["publish_job_id"],first["claim_token"]),
            ).fetchone()[0])
            con.execute("RESET ROLE")
            con.execute("UPDATE publish_jobs SET locked_at=now()-interval '16 minutes' WHERE id=%s",
                        (first["publish_job_id"],))
            con.execute("SET LOCAL ROLE service_role")
            self.assertEqual(con.execute(
                "SELECT public.recover_campaign_publications_f4e('staging')"
            ).fetchone()[0],1)
            self.assertEqual(con.execute(
                "SELECT status FROM publish_jobs WHERE id=%s",(first["publish_job_id"],)
            ).fetchone()[0],"unknown")
            self.assertIsNone(con.execute("SELECT public.claim_campaign_publication_f4e('staging','worker-b')").fetchone()[0])

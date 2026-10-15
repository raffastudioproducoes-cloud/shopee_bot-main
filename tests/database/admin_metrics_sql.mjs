import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { PGlite } from '../../.tmp/db-harness/node_modules/@electric-sql/pglite/dist/index.js'

// Banco descartável sem URL, rede, credenciais ou persistência em disco.
const db = new PGlite()
const migration = await readFile(new URL('../../database/migrations/051_admin_metrics_snapshot.sql', import.meta.url), 'utf8')
try {
  await db.exec(`
    CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;
    CREATE TABLE public.users(id uuid PRIMARY KEY, created_at timestamp NOT NULL);
    CREATE TABLE public.profiles(id uuid PRIMARY KEY, user_id uuid REFERENCES users(id), kind text, plan_tier text, created_at timestamp);
    CREATE TABLE public.request_logs(user_id uuid, created_at timestamp, status_code integer, duration_ms integer);
    CREATE TABLE public.audit_events(entity text, action text, created_at timestamp);
    CREATE TABLE public.schedulers(id integer);
    CREATE TABLE public.activities(activity_id integer, user_id uuid, created_at timestamp);
    INSERT INTO schedulers VALUES (1), (2);
    INSERT INTO activities VALUES (1, '00000000-0000-0000-0000-000000000001', CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
      (2, '00000000-0000-0000-0000-000000000001', CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
    INSERT INTO users VALUES
      ('00000000-0000-0000-0000-000000000001', CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
      ('00000000-0000-0000-0000-000000000002', (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '8 days'),
      ('00000000-0000-0000-0000-000000000003', (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '100 days');
    INSERT INTO profiles VALUES
      ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','principal','free',CURRENT_TIMESTAMP - interval '1 day'),
      ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','principal','premium',CURRENT_TIMESTAMP),
      ('10000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000002','principal','plus',CURRENT_TIMESTAMP);
    INSERT INTO request_logs VALUES
      ('00000000-0000-0000-0000-000000000001',(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '10 minutes',200,100),
      ('00000000-0000-0000-0000-000000000001',(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '2 minutes',200,200),
      (NULL,(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '1 day',500,300),
      (NULL,(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '10 days',200,400),
      ('00000000-0000-0000-0000-000000000002',(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + interval '1 day',500,900);
    INSERT INTO audit_events VALUES
      ('user','user_deleted',CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
      ('user','user_self_deleted',(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '10 days'),
      ('user','user_deleted',(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + interval '1 day');
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
    ALTER TABLE request_logs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
    GRANT USAGE ON SCHEMA public TO service_role;
    GRANT SELECT ON users, profiles, request_logs, audit_events, schedulers, activities TO service_role;
  `)
  await db.exec(migration)
  await db.exec(migration)
  for (const role of ['anon', 'authenticated']) {
    await db.exec(`SET ROLE ${role}`)
    await assert.rejects(db.query('SELECT public.admin_metrics_snapshot(7)'), /permission denied for function/)
    await assert.rejects(db.query('SELECT public.admin_capture_capacity()'), /permission denied for function/)
    await assert.rejects(db.query('SELECT * FROM public.admin_capacity_daily'), /permission denied/)
    await db.exec('RESET ROLE')
  }
  await db.exec('SET ROLE service_role')
  const snapshot = async days => (await db.query('SELECT public.admin_metrics_snapshot($1) AS snapshot', [days])).rows[0].snapshot
  const seven = await snapshot(7)
  assert.equal(seven.counts.accounts, 3, 'perfil principal duplicado não duplica contas')
  assert.equal(seven.scale.operations.scheduled, 2)
  assert.equal(seven.scale.operations.published_events, 1)
  assert.equal(seven.scale.operations.failed_events, 1)
  assert.equal(seven.scale.operations.publishing_accounts, 1)
  assert.equal(seven.scale.server_errors, 1)
  assert.equal(seven.scale.rate_limited_requests, 0)
  assert.equal(seven.scale.p99_latency_ms, 298)
  assert.equal(seven.scale.engagement.active_week, 1)
  assert.equal(seven.scale.engagement.previous_week, 0)
  assert.equal(seven.scale.engagement.returning_week, 0)
  assert.equal(seven.scale.capacity_history.length, 0)
  assert.equal(seven.scale.consumption.find(row => row.plan === 'free').requests, 2)
  await db.query('SELECT public.admin_capture_capacity()')
  await db.query('SELECT public.admin_capture_capacity()')
  const captured = await snapshot(7)
  assert.equal(captured.scale.capacity_history.length, 1, 'captura idempotente por dia')
  assert.ok(captured.scale.capacity_history[0].database_bytes > 0)
  assert.ok(seven.scale.database.tables.every(table => table.table_bytes >= 0 && table.index_bytes >= 0))
  assert.equal(seven.counts.free_accounts, 1)
  assert.equal(seven.counts.premium_accounts, 0)
  assert.equal(seven.counts.new_accounts, 1)
  assert.equal(seven.counts.requests, 3, 'amostra futura não integra o período atual')
  assert.equal(seven.counts.active_accounts, 1)
  assert.equal(seven.counts.deleted_accounts, 1)
  assert.equal(seven.counts.avg_latency_ms, 200)
  assert.equal(seven.daily.length, 7)
  assert.equal(seven.previous_period.requests, 1)
  assert.equal(seven.previous_period.registrations, 1)
  assert.equal(seven.previous_period.deletions, 1)
  assert.equal(seven.daily.reduce((sum, point) => sum + point.requests, 0), 3)
  assert.ok(seven.database.database_bytes > 0)
  assert.ok(!JSON.stringify(seven).includes('00000000-0000'))
  await db.exec('RESET ROLE')
  await db.exec(`INSERT INTO request_logs VALUES ('00000000-0000-0000-0000-000000000001', (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - interval '8 days', 200, 100)`)
  await db.exec('SET ROLE service_role')
  const returning = await snapshot(7)
  assert.equal(returning.scale.engagement.returning_week, 1)
  assert.equal(returning.scale.engagement.previous_week, 1)
  for (const [input, expected] of [[0, 7], [30, 30], [90, 90], [1000, 90], [null, 30]]) {
    assert.equal((await snapshot(input)).daily.length, expected)
  }
  await db.exec('RESET ROLE; DROP FUNCTION public.admin_metrics_snapshot(integer); DROP FUNCTION public.admin_capture_capacity(); DROP TABLE public.admin_capacity_daily')
  assert.equal((await db.query("SELECT to_regprocedure('public.admin_metrics_snapshot(integer)') AS installed")).rows[0].installed, null)
  console.log('PASS PostgreSQL descartável: migração, reaplicação, RLS/roles, agregados, períodos, privacidade e rollback')
} finally {
  await db.close()
}

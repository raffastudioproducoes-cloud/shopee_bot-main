-- Auto Orbital admin capacity observations (applied to production on 2026-10-30).
-- Schedule: daily 03:15 UTC = 00:15 America/Sao_Paulo (UTC-03).
-- Precondition: extension pg_cron and public.admin_capture_capacity().
-- Idempotent named job: rerunning updates its schedule; no extra jobs created.
-- This collects ONLY aggregate DB bytes / observed connections. No IPs/users.
SELECT cron.schedule(
  'auto-orbital-admin-capacity-v1',
  '15 3 * * *',
  'SELECT public.admin_capture_capacity();'
);
-- Initial capture, executed separately after deploying the scheduled job:
-- SELECT public.admin_capture_capacity();
-- Rollback (preserves collected history):
-- SELECT cron.unschedule('auto-orbital-admin-capacity-v1');

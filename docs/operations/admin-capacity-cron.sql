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
-- Initial capture was successfully executed on 2026-10-30 (Brasilia).
-- Result: one observed row; do not backfill fictitious prior dates.
-- This job captures a daily point, not continuous peaks or total disk quota.
-- To check the job and real execution outcomes (read-only):
-- SELECT jobid,jobname,schedule,active FROM cron.job
-- WHERE jobname='auto-orbital-admin-capacity-v1';
-- SELECT j.jobname,r.status,r.start_time,r.end_time,r.return_message
-- FROM cron.job_run_details r JOIN cron.job j ON j.jobid=r.jobid
-- WHERE j.jobname='auto-orbital-admin-capacity-v1'
-- ORDER BY r.start_time DESC LIMIT 10;
-- SELECT day,collected_at,database_bytes,observed_connections
-- FROM public.admin_capacity_daily ORDER BY day DESC LIMIT 10;
-- Rollback (preserves collected history):
-- SELECT cron.unschedule('auto-orbital-admin-capacity-v1');

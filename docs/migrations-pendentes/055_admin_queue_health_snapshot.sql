-- Admin-only aggregates for the durable publication queue.
-- No content, user identifiers, provider IDs, errors or tokens leave this RPC.
-- SECURITY INVOKER + service_role-only EXECUTE; no privileged browser access.
CREATE OR REPLACE FUNCTION public.admin_queue_health_snapshot()
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = ''
AS $$
  SELECT jsonb_build_object(
    'counts', jsonb_build_object(
      'total', count(*),
      'pending', count(*) FILTER (WHERE j.status = 'pending'),
      'running', count(*) FILTER (WHERE j.status = 'running'),
      'unknown', count(*) FILTER (WHERE j.status = 'unknown'),
      'failed', count(*) FILTER (WHERE j.status = 'failed'),
      'succeeded', count(*) FILTER (
          WHERE j.status = 'succeeded'
          AND coalesce(j.last_error, '') NOT LIKE 'MANUAL_CONFIRMED; %'),
      'manually_confirmed', count(*) FILTER (
          WHERE j.status = 'succeeded'
          AND coalesce(j.last_error, '') LIKE 'MANUAL_CONFIRMED; %'),
      'multiple_attempts', count(*) FILTER (WHERE j.attempt > 1)
    ),
    'oldest_unknown_minutes', (
      SELECT round(max(greatest(0, extract(epoch FROM (now() - coalesce(u.finished_at, u.created_at))) / 60)))::integer
      FROM public.publish_jobs u WHERE u.status = 'unknown'
    ),
    'oldest_running_minutes', (
      SELECT round(max(greatest(0, extract(epoch FROM (now() - coalesce(r.started_at, r.created_at))) / 60)))::integer
      FROM public.publish_jobs r WHERE r.status = 'running'
    ),
    'last_started_at', max(j.started_at),
    'collected_at', now()
  )
  FROM public.publish_jobs j;
$$;

REVOKE ALL ON FUNCTION public.admin_queue_health_snapshot() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_queue_health_snapshot() TO service_role;

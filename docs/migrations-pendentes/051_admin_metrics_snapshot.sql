-- Somente agregados para o backend ADMIN. Não aplica migração nesta tarefa.
-- Rollback: DROP FUNCTION public.admin_metrics_snapshot(integer);
CREATE OR REPLACE FUNCTION public.admin_metrics_snapshot(lookback_days integer DEFAULT 30)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = ''
AS $$
WITH bounds AS (
    SELECT
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date AS today,
        greatest(7, least(90, coalesce(lookback_days, 30))) AS days,
        CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AS now_utc
), time_window AS (
    SELECT *, ((today - (days - 1))::timestamp AT TIME ZONE 'America/Sao_Paulo') AT TIME ZONE 'UTC' AS start_utc
    FROM bounds
), account_counts AS (
    SELECT
        count(*) AS accounts,
        count(*) FILTER (WHERE u.created_at >= w.start_utc) AS new_accounts,
        count(*) FILTER (WHERE p.plan_tier = 'free') AS free_accounts,
        count(*) FILTER (WHERE p.plan_tier = 'plus') AS plus_accounts,
        count(*) FILTER (WHERE p.plan_tier = 'premium') AS premium_accounts
    FROM public.users u
    LEFT JOIN LATERAL (
        SELECT plan_tier FROM public.profiles
        WHERE user_id = u.id AND kind = 'principal'
        ORDER BY created_at, id LIMIT 1
    ) p ON true
    CROSS JOIN time_window w
), log_counts AS (
    SELECT count(*) AS requests,
        count(*) FILTER (WHERE status_code >= 400) AS errors,
        avg(duration_ms) FILTER (WHERE duration_ms >= 0) AS avg_latency_ms,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) FILTER (WHERE duration_ms >= 0) AS p95_latency_ms
    FROM public.request_logs l CROSS JOIN time_window w WHERE l.created_at >= w.start_utc
), deletions AS (
    SELECT a.created_at
    FROM public.audit_events a CROSS JOIN time_window w
    WHERE a.entity = 'user' AND a.action IN ('user_deleted', 'user_self_deleted') AND a.created_at >= w.start_utc
), daily_accounts AS (
    SELECT ((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date AS day, count(*) AS value
    FROM public.users u CROSS JOIN time_window w WHERE u.created_at >= w.start_utc GROUP BY 1
), daily_deletions AS (
    SELECT ((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date AS day, count(*) AS value
    FROM deletions GROUP BY 1
), daily_requests AS (
    SELECT ((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date AS day, count(*) AS value
    FROM public.request_logs l CROSS JOIN time_window w WHERE l.created_at >= w.start_utc GROUP BY 1
), days AS (
    SELECT today - offset_day AS day FROM time_window CROSS JOIN LATERAL generate_series(0, days - 1) AS offset_day
)
SELECT jsonb_build_object(
    'counts', (SELECT to_jsonb(a) || to_jsonb(l) || jsonb_build_object(
        'deleted_accounts', (SELECT count(*) FROM deletions),
        'active_accounts', (SELECT count(DISTINCT r.user_id) FROM public.request_logs r
            JOIN public.users u ON u.id = r.user_id CROSS JOIN time_window w
            WHERE r.created_at >= w.now_utc - interval '5 minutes' AND r.status_code < 400)
    ) FROM account_counts a CROSS JOIN log_counts l),
    'daily', (SELECT jsonb_agg(jsonb_build_object(
        'date', d.day, 'registrations', coalesce(a.value, 0),
        'deletions', coalesce(x.value, 0), 'requests', coalesce(r.value, 0)
    ) ORDER BY d.day) FROM days d
      LEFT JOIN daily_accounts a USING (day) LEFT JOIN daily_deletions x USING (day) LEFT JOIN daily_requests r USING (day)),
    'database', jsonb_build_object(
        'database_bytes', pg_database_size(current_database()),
        'connections', (SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE datname = current_database()),
        'max_connections', current_setting('max_connections')::integer
    )
);
$$;

REVOKE ALL ON FUNCTION public.admin_metrics_snapshot(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_metrics_snapshot(integer) TO service_role;

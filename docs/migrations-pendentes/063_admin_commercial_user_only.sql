-- 063: Admin commercial metrics count USER customers only.
-- Infrastructure request/error/storage metrics continue to cover the entire platform.
-- This migration preserves the existing RPC response shape for the Admin Dashboard.

CREATE OR REPLACE FUNCTION public.admin_metrics_snapshot(lookback_days integer DEFAULT 30)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO ''
AS $function$
WITH bounds AS (
    SELECT
        (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date AS today,
        greatest(7, least(90, coalesce(lookback_days, 30))) AS days,
        CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AS now_utc
), time_window AS (
    SELECT *,
        ((today - (days - 1))::timestamp AT TIME ZONE 'America/Sao_Paulo') AT TIME ZONE 'UTC' AS start_utc,
        ((today - (days * 2 - 1))::timestamp AT TIME ZONE 'America/Sao_Paulo') AT TIME ZONE 'UTC' AS previous_start_utc
    FROM bounds
), weekly_accounts AS (
    SELECT DISTINCT r.user_id,
        r.created_at >= w.now_utc - interval '7 days' AS current_week
    FROM public.request_logs r JOIN public.users u ON u.id = r.user_id CROSS JOIN time_window w
    WHERE u.access::text = 'USER' AND r.status_code < 400 AND r.created_at BETWEEN w.now_utc - interval '14 days' AND w.now_utc
), account_counts AS (
    SELECT
        count(*) AS accounts,
        count(*) FILTER (WHERE u.created_at >= w.start_utc AND u.created_at <= w.now_utc) AS new_accounts,
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
    WHERE u.access::text = 'USER'
), log_counts AS (
    SELECT count(*) AS requests,
        count(*) FILTER (WHERE status_code >= 400) AS errors,
        avg(duration_ms) FILTER (WHERE duration_ms >= 0) AS avg_latency_ms,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) FILTER (WHERE duration_ms >= 0) AS p95_latency_ms
    FROM public.request_logs l CROSS JOIN time_window w WHERE l.created_at >= w.start_utc AND l.created_at <= w.now_utc
), deletions AS (
    SELECT a.created_at
    FROM public.audit_events a CROSS JOIN time_window w
    WHERE a.entity = 'user' AND a.action IN ('user_deleted', 'user_self_deleted') AND a.old_value->>'access' = 'USER' AND a.created_at >= w.start_utc AND a.created_at <= w.now_utc
), daily_accounts AS (
    SELECT ((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date AS day, count(*) AS value
    FROM public.users u CROSS JOIN time_window w WHERE u.access::text = 'USER' AND u.created_at >= w.start_utc AND u.created_at <= w.now_utc GROUP BY 1
), daily_deletions AS (
    SELECT ((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date AS day, count(*) AS value
    FROM deletions GROUP BY 1
), daily_requests AS (
    SELECT ((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date AS day, count(*) AS value
    FROM public.request_logs l CROSS JOIN time_window w WHERE l.created_at >= w.start_utc AND l.created_at <= w.now_utc GROUP BY 1
), days AS (
    SELECT today - offset_day AS day FROM time_window CROSS JOIN LATERAL generate_series(0, days - 1) AS offset_day
)
SELECT jsonb_build_object(
    'scale', jsonb_build_object(
        'capacity_history', (SELECT coalesce(jsonb_agg(jsonb_build_object('date', h.day, 'database_bytes', h.database_bytes, 'observed_connections', h.observed_connections) ORDER BY h.day), '[]'::jsonb) FROM public.admin_capacity_daily h CROSS JOIN time_window w WHERE h.day BETWEEN w.today - (w.days - 1) AND w.today),
        'consumption', (SELECT coalesce(jsonb_agg(to_jsonb(c)), '[]'::jsonb) FROM (
            SELECT coalesce(p.plan_tier, 'unknown') AS plan, count(*) AS requests,
                coalesce(sum(l.duration_ms) FILTER (WHERE l.duration_ms >= 0), 0) AS request_duration_ms
            FROM public.request_logs l JOIN public.users u ON u.id = l.user_id
            LEFT JOIN LATERAL (SELECT plan_tier FROM public.profiles WHERE user_id = u.id AND kind = 'principal' ORDER BY created_at, id LIMIT 1) p ON true
            CROSS JOIN time_window w WHERE u.access::text = 'USER' AND l.created_at BETWEEN w.start_utc AND w.now_utc
            GROUP BY coalesce(p.plan_tier, 'unknown')
        ) c),
        'server_errors', (SELECT count(*) FROM public.request_logs l CROSS JOIN time_window w WHERE l.created_at BETWEEN w.start_utc AND w.now_utc AND l.status_code >= 500),
        'rate_limited_requests', (SELECT count(*) FROM public.request_logs l CROSS JOIN time_window w WHERE l.created_at BETWEEN w.start_utc AND w.now_utc AND l.status_code = 429),
        'p99_latency_ms', (SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY l.duration_ms) FROM public.request_logs l CROSS JOIN time_window w WHERE l.created_at BETWEEN w.start_utc AND w.now_utc AND l.duration_ms >= 0),
        'database', jsonb_build_object(
            'blocked_connections', (SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE datname = current_database() AND cardinality(pg_catalog.pg_blocking_pids(pid)) > 0),
            'oldest_transaction_seconds', (SELECT greatest(0, extract(epoch FROM CURRENT_TIMESTAMP - min(xact_start))) FROM pg_catalog.pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()),
            'tables', (SELECT coalesce(jsonb_agg(jsonb_build_object('name', relname, 'table_bytes', pg_catalog.pg_table_size(relid), 'index_bytes', pg_catalog.pg_indexes_size(relid)) ORDER BY pg_catalog.pg_total_relation_size(relid) DESC), '[]'::jsonb)
                FROM pg_catalog.pg_statio_user_tables WHERE schemaname = 'public' AND relname IN ('users','profiles','posts','activities','request_logs','audit_events','schedulers','medias'))
        ),
        'operations', jsonb_build_object(
            'scheduled', (SELECT count(*) FROM public.schedulers),
            'published_events', (SELECT count(*) FROM public.activities a CROSS JOIN time_window w WHERE a.activity_id = 1 AND a.created_at BETWEEN w.start_utc AND w.now_utc),
            'failed_events', (SELECT count(*) FROM public.activities a CROSS JOIN time_window w WHERE a.activity_id = 2 AND a.created_at BETWEEN w.start_utc AND w.now_utc),
            'publishing_accounts', (SELECT count(DISTINCT a.user_id) FROM public.activities a JOIN public.users u ON u.id = a.user_id CROSS JOIN time_window w WHERE u.access::text = 'USER' AND a.activity_id = 1 AND a.created_at BETWEEN w.start_utc AND w.now_utc)
        ),
        'engagement', (SELECT jsonb_build_object(
            'active_week', (SELECT count(*) FROM weekly_accounts WHERE current_week),
            'previous_week', (SELECT count(*) FROM weekly_accounts WHERE NOT current_week),
            'returning_week', (SELECT count(*) FROM weekly_accounts a JOIN weekly_accounts p USING (user_id) WHERE a.current_week AND NOT p.current_week)))
    ),
    'previous_period', (SELECT jsonb_build_object(
        'starts_on', w.today - (w.days * 2 - 1), 'ends_on', w.today - w.days,
        'registrations', (SELECT count(*) FROM public.users u WHERE u.access::text = 'USER' AND u.created_at >= w.previous_start_utc AND u.created_at < w.start_utc),
        'requests', (SELECT count(*) FROM public.request_logs l WHERE l.created_at >= w.previous_start_utc AND l.created_at < w.start_utc),
        'errors', (SELECT count(*) FROM public.request_logs l WHERE l.created_at >= w.previous_start_utc AND l.created_at < w.start_utc AND l.status_code >= 400),
        'deletions', (SELECT count(*) FROM public.audit_events a WHERE a.entity = 'user' AND a.action IN ('user_deleted', 'user_self_deleted') AND a.old_value->>'access' = 'USER' AND a.created_at >= w.previous_start_utc AND a.created_at < w.start_utc)
    ) FROM time_window w),
    'counts', (SELECT to_jsonb(a) || to_jsonb(l) || jsonb_build_object(
        'deleted_accounts', (SELECT count(*) FROM deletions),
        'active_accounts', (SELECT count(DISTINCT r.user_id) FROM public.request_logs r
            JOIN public.users u ON u.id = r.user_id CROSS JOIN time_window w
            WHERE u.access::text = 'USER' AND r.created_at >= w.now_utc - interval '5 minutes' AND r.created_at <= w.now_utc AND r.status_code < 400)
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
$function$
;

CREATE OR REPLACE FUNCTION public.admin_acquisition_aggregates()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
 SELECT jsonb_build_object(
   'status','available',
   'source','self_reported',
   'minimum_group_size',3,
   'declared_total',(SELECT count(*) FROM public.account_acquisition_sources a JOIN public.users u ON u.id=a.user_id WHERE u.access::text='USER'),
   'groups',coalesce((
    SELECT jsonb_agg(jsonb_build_object('source',source,'accounts',accounts) ORDER BY source)
    FROM (
     SELECT a.source,count(*) AS accounts
     FROM public.account_acquisition_sources a JOIN public.users u ON u.id=a.user_id
     WHERE u.access::text='USER'
     GROUP BY a.source HAVING count(*) >= 3
    ) g
   ),'[]'::jsonb)
 );
$function$
;

-- Restrict the privileged acquisition RPC to the backend service role.
REVOKE ALL ON FUNCTION public.admin_acquisition_aggregates() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_acquisition_aggregates() TO service_role;

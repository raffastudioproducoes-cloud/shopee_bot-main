-- 062: client-only admin geography and anonymous, durable deletion counters.
-- Backfill from existing audit events, then count future USER deletions atomically.
-- No user_id, username, GPS point, address or region is retained in the daily history.
-- Schema intended for service_role API access only.

LOCK TABLE public.users IN SHARE ROW EXCLUSIVE MODE;

CREATE TABLE IF NOT EXISTS public.admin_deleted_users_daily (
    day date PRIMARY KEY,
    deleted_users bigint NOT NULL DEFAULT 0 CHECK (deleted_users >= 0)
);
ALTER TABLE public.admin_deleted_users_daily ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.admin_deleted_users_daily FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.admin_deleted_users_daily TO service_role;

-- Existing audit events may contain historical identifiers, but this new table never does.
-- Deduplicate by deleted account to guard against repeated audit events for one account.
INSERT INTO public.admin_deleted_users_daily (day, deleted_users)
SELECT deleted_on, COUNT(*)::bigint
FROM (
    SELECT DISTINCT ON (entity_id) entity_id, created_at::date AS deleted_on
    FROM public.audit_events
    WHERE action IN ('user_deleted','user_self_deleted')
      AND entity = 'user'
      AND old_value->>'access' = 'USER'
      AND entity_id IS NOT NULL
    ORDER BY entity_id, created_at
) historical
GROUP BY deleted_on
ON CONFLICT (day) DO NOTHING;

CREATE OR REPLACE FUNCTION public.track_deleted_user_daily()
RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    IF OLD.access::text = 'USER' THEN
        INSERT INTO public.admin_deleted_users_daily (day, deleted_users)
        VALUES ((now() AT TIME ZONE 'UTC')::date, 1)
        ON CONFLICT (day) DO UPDATE
        SET deleted_users = public.admin_deleted_users_daily.deleted_users + 1;
    END IF;
    RETURN OLD;
END;
$$;
REVOKE ALL ON FUNCTION public.track_deleted_user_daily() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.track_deleted_user_daily() TO service_role;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'public.users'::regclass
          AND tgname = 'track_deleted_user_daily'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER track_deleted_user_daily
        AFTER DELETE ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.track_deleted_user_daily();
    END IF;
END;
$$;

-- The regional activity function always excludes administrators. Small regions stay hidden.
CREATE OR REPLACE FUNCTION public.admin_region_aggregates()
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
 WITH counts AS (
  SELECT p.region, count(*)::integer AS total,
   count(*) FILTER (WHERE EXISTS (
     SELECT 1 FROM public.request_logs l
     WHERE l.user_id=p.user_id
       AND l.created_at >= (now() AT TIME ZONE 'UTC')-interval '5 minutes'
       AND l.status_code < 400
   ))::integer AS active
  FROM public.account_region_preferences p
  JOIN public.users u ON u.id=p.user_id
  WHERE u.access::text='USER'
  GROUP BY p.region
 ), visible AS (
  SELECT region,active,(total-active)::integer AS inactive
  FROM counts WHERE total>=3 AND region IN ('BR-RJ','BR-SP','BR-MG','BR-BA','PT','US','GB','DE','JP','AU')
 )
 SELECT jsonb_build_object(
  'status','available', 'source','voluntary', 'updated_at',now(),
  'minimum_group_size',3,
  'regions',coalesce((SELECT jsonb_agg(jsonb_build_object(
    'region',region,'online',active,'offline',inactive,'deleted',0
   ) ORDER BY region) FROM visible),'[]'::jsonb)
 );
$$;
REVOKE ALL ON FUNCTION public.admin_region_aggregates() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_region_aggregates() TO service_role;

-- Aggregate totals include zero or one customer, because this endpoint is ADMIN-only.
-- Precise account IDs are never returned. Individual GPS points require recorded consent
-- and are limited to the latest 500 for predictable response size.
CREATE OR REPLACE FUNCTION public.admin_client_geo_overview()
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
WITH clients AS (
  SELECT count(*)::integer AS total,
    count(*) FILTER (WHERE EXISTS (
      SELECT 1 FROM public.request_logs l
      WHERE l.user_id=u.id
        AND l.created_at >= (now() AT TIME ZONE 'UTC') - interval '5 minutes'
        AND l.status_code < 400
    ))::integer AS recent
  FROM public.users u WHERE u.access::text='USER'
),
gps AS (
  SELECT count(*)::integer AS total
  FROM public.account_location_sharing l
  JOIN public.users u ON u.id=l.user_id
  WHERE u.access::text='USER' AND l.choice='accepted'
),
gps_points AS (
  SELECT coalesce(jsonb_agg(jsonb_build_object(
    'account', left(l.user_id::text,8),
    'latitude', l.latitude,
    'longitude', l.longitude,
    'accuracy_m', l.accuracy_m,
    'collected_at', l.collected_at
  ) ORDER BY l.collected_at DESC, l.user_id),'[]'::jsonb) AS rows
  FROM (
    SELECT l.user_id, l.latitude, l.longitude, l.accuracy_m, l.collected_at
    FROM public.account_location_sharing l
    JOIN public.users u ON u.id=l.user_id
    WHERE u.access::text='USER' AND l.choice='accepted'
    ORDER BY l.collected_at DESC, l.user_id
    LIMIT 500
  ) l
),
regions AS (
  SELECT count(*)::integer AS total
  FROM public.account_region_preferences p
  JOIN public.users u ON u.id=p.user_id
  WHERE u.access::text='USER'
),
deletions AS (
  SELECT coalesce(sum(deleted_users),0)::bigint AS total, min(day) AS since
  FROM public.admin_deleted_users_daily
)
SELECT jsonb_build_object(
  'status','available',
  'updated_at',now(),
  'customers_total',(SELECT total FROM clients),
  'recent_active',(SELECT recent FROM clients),
  'gps_points_total',(SELECT total FROM gps),
  'region_participants',(SELECT total FROM regions),
  'deleted_total',(SELECT total FROM deletions),
  'deleted_since',(SELECT since FROM deletions),
  'points',(SELECT rows FROM gps_points)
);
$$;
REVOKE ALL ON FUNCTION public.admin_client_geo_overview() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_client_geo_overview() TO service_role;

COMMENT ON TABLE public.admin_deleted_users_daily IS
'Daily historical number of deleted USER accounts; no personal information or coordinates.';

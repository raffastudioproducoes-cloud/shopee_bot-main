-- 058: voluntary region preference (not IP or GPS), owner-only API.
CREATE TABLE IF NOT EXISTS public.account_region_preferences (
 user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
 region text NOT NULL CHECK (region IN ('BR-RJ','BR-SP','BR-MG','BR-BA','BR-OTHER','PT','US','GB','DE','JP','AU','OTHER')),
 consented_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.account_region_preferences ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.account_region_preferences FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.account_region_preferences TO service_role;

CREATE OR REPLACE FUNCTION public.admin_region_aggregates()
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=''
AS $$
 WITH counts AS (
  SELECT p.region, count(*)::integer AS total,
   count(*) FILTER (WHERE EXISTS (
     SELECT 1 FROM public.request_logs l
     WHERE l.user_id=p.user_id
       AND l.created_at>= (now() AT TIME ZONE 'UTC')-interval '5 minutes'
       AND l.status_code<400
   ))::integer AS active
  FROM public.account_region_preferences p JOIN public.users u ON u.id=p.user_id
  GROUP BY p.region
 ), visible AS (
  SELECT region,active,(total-active)::integer AS inactive
  FROM counts WHERE total>=3 AND region IN ('BR-RJ','BR-SP','BR-MG','BR-BA','PT','US','GB','DE','JP','AU')
 )
 SELECT jsonb_build_object(
  'status','available',
  'source','voluntary',
  'updated_at',now(),
  'minimum_group_size',3,
  'regions',coalesce((SELECT jsonb_agg(jsonb_build_object(
    'region',region,'online',active,'offline',inactive,'deleted',0
   ) ORDER BY region) FROM visible),'[]'::jsonb)
 );
$$;
REVOKE ALL ON FUNCTION public.admin_region_aggregates() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_region_aggregates() TO service_role;

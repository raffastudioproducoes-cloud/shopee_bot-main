-- 059: user-declared, revocable marketing acquisition source.
-- Does not process referrers, tracking cookies, IPs, ad IDs or UTMs.
CREATE TABLE IF NOT EXISTS public.account_acquisition_sources (
 user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
 source text NOT NULL CHECK (source IN ('search','social','referral','direct','other')),
 declared_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.account_acquisition_sources ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.account_acquisition_sources FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.account_acquisition_sources TO service_role;
CREATE OR REPLACE FUNCTION public.admin_acquisition_aggregates()
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=''
AS $$
 SELECT jsonb_build_object(
   'status','available',
   'source','self_reported',
   'minimum_group_size',3,
   'declared_total',(SELECT count(*) FROM public.account_acquisition_sources a JOIN public.users u ON u.id=a.user_id),
   'groups',coalesce((
    SELECT jsonb_agg(jsonb_build_object('source',source,'accounts',accounts) ORDER BY source)
    FROM (
     SELECT a.source,count(*) AS accounts
     FROM public.account_acquisition_sources a JOIN public.users u ON u.id=a.user_id
     GROUP BY a.source HAVING count(*) >= 3
    ) g
   ),'[]'::jsonb)
 );
$$;
REVOKE ALL ON FUNCTION public.admin_acquisition_aggregates() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_acquisition_aggregates() TO service_role;

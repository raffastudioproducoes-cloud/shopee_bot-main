-- F4E2: one atomic materialization, independently retained assets and guarded worker.
BEGIN;
SET LOCAL lock_timeout = '5s';

CREATE TABLE public.campaign_reservation_assets_f4e (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reservation_id uuid NOT NULL REFERENCES public.campaign_reservations_f4e(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  product_id integer NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
  source_id text NOT NULL,
  media_id integer NOT NULL UNIQUE REFERENCES public.medias(id) ON DELETE RESTRICT,
  storage_key text NOT NULL UNIQUE,
  networks text[] NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(reservation_id,source_id),
  CHECK (length(source_id) BETWEEN 1 AND 150),
  CHECK (cardinality(networks) BETWEEN 1 AND 5),
  CHECK (networks <@ ARRAY['threads','x','facebook','instagram','tiktok']::text[])
);
CREATE INDEX campaign_reservation_assets_by_product_f4e
  ON public.campaign_reservation_assets_f4e(reservation_id,product_id);
ALTER TABLE public.campaign_reservation_assets_f4e ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.campaign_reservation_assets_f4e FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT,INSERT ON public.campaign_reservation_assets_f4e TO service_role;

CREATE TABLE public.campaign_oauth_checks_f4e (
  reservation_id uuid NOT NULL REFERENCES public.campaign_reservations_f4e(id) ON DELETE CASCADE,
  network text NOT NULL CHECK (network IN ('threads','x','facebook','instagram','tiktok')),
  verified_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (reservation_id,network)
);
ALTER TABLE public.campaign_oauth_checks_f4e ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.campaign_oauth_checks_f4e FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT,INSERT ON public.campaign_oauth_checks_f4e TO service_role;

-- Backend can only attest media already copied into an owner-specific prefix.
CREATE FUNCTION public.record_campaign_asset_f4e(
  p_user uuid, p_profile uuid, p_reservation uuid, p_product integer,
  p_source text, p_key text, p_name text, p_type text, p_size integer,
  p_networks text[]
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_res record; v_existing integer; v_media integer;
BEGIN
  SELECT * INTO v_res FROM public.campaign_reservations_f4e
   WHERE id=p_reservation AND user_id=p_user AND profile_id=p_profile FOR UPDATE;
  IF NOT FOUND OR v_res.lifecycle <> 'preparing'
    OR v_res.status <> 'reserved_no_dispatch'
    OR p_key NOT LIKE ('campaign-locked/'||p_user::text||'/'||p_profile::text||'/'||p_reservation::text||'/%')
    OR p_size < 1 OR p_size > 52428800
    OR p_type NOT IN ('IMAGE','VIDEO')
    OR p_networks IS NULL OR cardinality(p_networks)=0
  THEN RAISE EXCEPTION 'invalid_campaign_asset' USING ERRCODE='P0001'; END IF;
  IF NOT EXISTS (
    SELECT 1 FROM jsonb_array_elements(v_res.draft_snapshot->'items') i
      WHERE (i->>'product_id')::integer=p_product
  ) THEN RAISE EXCEPTION 'product_not_in_campaign' USING ERRCODE='P0001'; END IF;
  IF p_source LIKE 'draft:%' AND NOT EXISTS (
    SELECT 1 FROM jsonb_array_elements(v_res.media_snapshot) m
    WHERE 'draft:'||(m->>'id')=p_source AND (m->>'product_id')::integer=p_product
      AND m->>'status'='ready'
  ) THEN RAISE EXCEPTION 'media_not_in_snapshot' USING ERRCODE='P0001'; END IF;
  IF p_source LIKE 'shopee:%' AND NOT EXISTS (
    SELECT 1 FROM jsonb_array_elements(v_res.draft_snapshot->'items') i
    WHERE (i->>'product_id')::integer=p_product AND i->>'use_shopee_image'='true'
      AND NULLIF(i->>'source_image','') IS NOT NULL
      AND p_source='shopee:'||p_product::text
  ) THEN RAISE EXCEPTION 'image_not_in_snapshot' USING ERRCODE='P0001'; END IF;
  IF p_source NOT LIKE 'draft:%' AND p_source NOT LIKE 'shopee:%'
  THEN RAISE EXCEPTION 'invalid_asset_source' USING ERRCODE='P0001'; END IF;
  SELECT media_id INTO v_existing FROM public.campaign_reservation_assets_f4e
   WHERE reservation_id=p_reservation AND source_id=p_source;
  IF FOUND THEN RETURN v_existing; END IF;
  INSERT INTO public.medias(file_name,file_path,size,type,user_id,profile_id)
    VALUES(p_name,'storage://post-media/'||p_key,p_size,p_type::public.mediatype,p_user,p_profile)
    RETURNING id INTO v_media;
  INSERT INTO public.campaign_reservation_assets_f4e
    (reservation_id,user_id,profile_id,product_id,source_id,media_id,storage_key,networks)
    VALUES(p_reservation,p_user,p_profile,p_product,p_source,v_media,p_key,p_networks);
  RETURN v_media;
END; $$;

-- Materialize everything, including post relations, in the SAME transaction;
-- activation never exposes a partially built campaign to its worker.
CREATE FUNCTION public.materialize_campaign_f4e(
  p_user uuid, p_profile uuid, p_reservation uuid, p_environment text
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_res record; v_slot record; v_item jsonb; v_post integer;
  v_scheduler uuid; v_job uuid; v_count integer := 0; v_missing integer;
BEGIN
  IF p_environment NOT IN ('production','staging')
  THEN RAISE EXCEPTION 'invalid_environment' USING ERRCODE='P0001'; END IF;
  PERFORM 1 FROM public.users WHERE id=p_user FOR UPDATE;
  SELECT * INTO v_res FROM public.campaign_reservations_f4e
    WHERE id=p_reservation AND user_id=p_user AND profile_id=p_profile FOR UPDATE;
  IF NOT FOUND OR v_res.status <> 'reserved_no_dispatch'
  THEN RAISE EXCEPTION 'reservation_not_owned' USING ERRCODE='P0001'; END IF;
  IF v_res.lifecycle='active' AND v_res.source_environment=p_environment
  THEN RETURN (SELECT count(*)::integer FROM public.campaign_network_slots_f4e WHERE reservation_id=p_reservation); END IF;
  IF v_res.lifecycle <> 'preparing'
  THEN RAISE EXCEPTION 'campaign_not_preparing' USING ERRCODE='P0001'; END IF;
  IF EXISTS (
    SELECT 1 FROM public.campaign_network_slots_f4e s
    LEFT JOIN public.campaign_oauth_checks_f4e c
      ON c.reservation_id=s.reservation_id AND c.network=s.network
       AND c.verified_at > now()-interval '5 minutes'
    WHERE s.reservation_id=p_reservation AND c.reservation_id IS NULL
  ) THEN RAISE EXCEPTION 'oauth_not_verified' USING ERRCODE='P0001'; END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_array_elements(v_res.media_snapshot) m
      WHERE NOT EXISTS (
        SELECT 1 FROM public.campaign_reservation_assets_f4e a
        WHERE a.reservation_id=p_reservation AND a.source_id='draft:'||(m->>'id')
      )
  ) THEN RAISE EXCEPTION 'media_not_retained' USING ERRCODE='P0001'; END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_array_elements(v_res.draft_snapshot->'items') i
    WHERE i->>'use_shopee_image'='true' AND NULLIF(i->>'source_image','') IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM public.campaign_reservation_assets_f4e a
      WHERE a.reservation_id=p_reservation
        AND a.source_id='shopee:'||(i->>'product_id')
    )
  ) THEN RAISE EXCEPTION 'shopee_image_not_retained' USING ERRCODE='P0001'; END IF;
  IF EXISTS (
    SELECT 1 FROM public.campaign_network_slots_f4e s
    WHERE s.reservation_id=p_reservation AND NOT EXISTS (
      SELECT 1 FROM public.campaign_reservation_assets_f4e a
      WHERE a.reservation_id=s.reservation_id AND a.product_id=s.product_id
        AND s.network=ANY(a.networks)
    ) AND s.network IN ('instagram','tiktok')
  ) THEN RAISE EXCEPTION 'required_network_media_missing' USING ERRCODE='P0001'; END IF;
  FOR v_slot IN
    SELECT * FROM public.campaign_network_slots_f4e
    WHERE reservation_id=p_reservation ORDER BY planned_at,id FOR UPDATE
  LOOP
    SELECT i INTO v_item FROM jsonb_array_elements(v_res.draft_snapshot->'items') i
    WHERE (i->>'product_id')::integer=v_slot.product_id;
    INSERT INTO public.posts(text,user_id,profile_id,network,publish_immediately)
    VALUES(
      CASE WHEN position(COALESCE(v_item->>'affiliate_link','') IN v_slot.content_text)>0
        THEN v_slot.content_text
        ELSE concat_ws(E'\n',nullif(v_slot.content_text,''),nullif(v_item->>'affiliate_link',''))
      END,
      p_user,p_profile,v_slot.network,false
    ) RETURNING id INTO v_post;
    INSERT INTO public.posts_products(post_id,product_id,display_order)
      VALUES(v_post,v_slot.product_id,0);
    INSERT INTO public.posts_medias(post_id,media_id,display_order)
      SELECT v_post,a.media_id,row_number() OVER (ORDER BY a.created_at,a.id)-1
      FROM public.campaign_reservation_assets_f4e a
      WHERE a.reservation_id=p_reservation AND a.product_id=v_slot.product_id
        AND v_slot.network=ANY(a.networks);
    INSERT INTO public.schedulers(
      func,trigger,run_date,post_id,user_id,profile_id,environment,dispatch_mode,publication_origin
    ) VALUES(
      CASE v_slot.network WHEN 'threads' THEN 'bot_post'
        ELSE 'bot_post_'||v_slot.network END,
      'date',v_slot.planned_at AT TIME ZONE 'America/Sao_Paulo',
      v_post,p_user,p_profile,p_environment,'legacy','campaign'
    ) RETURNING id INTO v_scheduler;
    INSERT INTO public.publish_jobs(
      scheduler_id,post_id,user_id,profile_id,network,
      idempotency_key,scheduled_for,publication_origin
    ) VALUES(
      v_scheduler,v_post,p_user,p_profile,v_slot.network,
      'campaign:'||v_slot.id::text,v_slot.planned_at,'campaign'
    ) RETURNING id INTO v_job;
    UPDATE public.campaign_network_slots_f4e
      SET post_id=v_post,scheduler_id=v_scheduler,publish_job_id=v_job
    WHERE id=v_slot.id;
    v_count:=v_count+1;
  END LOOP;
  PERFORM public.activate_campaign_networks_f4e(p_user,p_profile,p_reservation,p_environment);
  RETURN v_count;
END; $$;

-- The old entrypoint must not bypass media/OAuth/manifests.
REVOKE EXECUTE ON FUNCTION public.activate_campaign_networks_f4e(uuid,uuid,uuid,text) FROM service_role;
REVOKE ALL ON FUNCTION public.record_campaign_asset_f4e(uuid,uuid,uuid,integer,text,text,text,text,integer,text[])
 FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.materialize_campaign_f4e(uuid,uuid,uuid,text)
 FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.record_campaign_asset_f4e(uuid,uuid,uuid,integer,text,text,text,text,integer,text[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.materialize_campaign_f4e(uuid,uuid,uuid,text) TO service_role;

-- Terminal completion and human-readable progression are derived from each network job.
CREATE VIEW public.campaign_progress_f4e WITH (security_invoker = true) AS
SELECT r.id AS reservation_id,r.user_id,r.profile_id,r.lifecycle,r.activated_at,
  count(s.id)::integer AS total,
  count(s.id) FILTER (WHERE s.state='planned')::integer AS planned,
  count(s.id) FILTER (WHERE s.state='running')::integer AS running,
  count(s.id) FILTER (WHERE s.state='succeeded')::integer AS succeeded,
  count(s.id) FILTER (WHERE s.state='failed')::integer AS failed,
  count(s.id) FILTER (WHERE s.state='unknown')::integer AS unknown,
  count(s.id) FILTER (WHERE s.state='cancelled')::integer AS cancelled
FROM public.campaign_reservations_f4e r
LEFT JOIN public.campaign_network_slots_f4e s ON s.reservation_id=r.id
GROUP BY r.id;
REVOKE ALL ON public.campaign_progress_f4e FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT ON public.campaign_progress_f4e TO service_role;

COMMIT;

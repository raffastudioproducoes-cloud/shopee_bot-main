-- PROPOSTA R1 PARA REVISAO. NAO EXECUTAR, NAO MOVER PARA migrations.
-- Banco compartilhado; teste PostgreSQL e revisao de seguranca sao gates obrigatorios.
BEGIN;
SET LOCAL lock_timeout = '10s';

CREATE TABLE public.campaign_reservations_f4e (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  draft_id uuid REFERENCES public.campaign_drafts(id) ON DELETE SET NULL,
  request_key text NOT NULL CHECK (length(request_key) BETWEEN 1 AND 200),
  request_payload jsonb NOT NULL CHECK (jsonb_typeof(request_payload) = 'object'),
  draft_snapshot jsonb NOT NULL CHECK (jsonb_typeof(draft_snapshot) = 'object'),
  media_snapshot jsonb NOT NULL CHECK (jsonb_typeof(media_snapshot) = 'array'),
  status text NOT NULL DEFAULT 'reserved_no_dispatch'
    CHECK (status IN ('reserved_no_dispatch','released')),
  dispatch_enabled boolean NOT NULL DEFAULT false CHECK (dispatch_enabled = false),
  created_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz,
  CHECK ((status = 'reserved_no_dispatch' AND released_at IS NULL)
      OR (status = 'released' AND released_at IS NOT NULL)),
  UNIQUE (user_id, request_key)
);
CREATE INDEX campaign_reservations_f4e_user_idx ON public.campaign_reservations_f4e(user_id, profile_id, status);
CREATE INDEX campaign_reservations_f4e_profile_idx ON public.campaign_reservations_f4e(profile_id);
CREATE INDEX campaign_reservations_f4e_draft_idx ON public.campaign_reservations_f4e(draft_id);

CREATE TABLE public.campaign_occurrences_f4e (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reservation_id uuid NOT NULL REFERENCES public.campaign_reservations_f4e(id) ON DELETE CASCADE,
  ordinal integer NOT NULL CHECK (ordinal BETWEEN 1 AND 450),
  planned_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','cancelled')),
  dispatch_enabled boolean NOT NULL DEFAULT false CHECK (dispatch_enabled = false),
  UNIQUE (reservation_id, ordinal)
);

ALTER TABLE public.campaign_reservations_f4e ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_occurrences_f4e ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.campaign_reservations_f4e, public.campaign_occurrences_f4e
  FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT ON public.campaign_reservations_f4e, public.campaign_occurrences_f4e TO service_role;
GRANT UPDATE (status, released_at) ON public.campaign_reservations_f4e TO service_role;
GRANT UPDATE (status) ON public.campaign_occurrences_f4e TO service_role;

-- RPCs exclusivamente para backend confiavel: service_role nao e identidade final.
-- Backend deve autenticar e autorizar a conta/perfil antes de invocar.
CREATE FUNCTION public.reserve_campaign_f4e(
  p_user_id uuid, p_profile_id uuid, p_draft_id uuid,
  p_revision integer, p_request_key text, p_occurrences jsonb
) RETURNS uuid LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_access text; v_tier text; v_limit integer; v_id uuid;
  v_payload jsonb; v_old jsonb; v_draft jsonb; v_media jsonb;
BEGIN
  IF p_user_id IS NULL OR p_profile_id IS NULL OR p_draft_id IS NULL
     OR p_revision IS NULL OR p_revision < 1 OR p_request_key IS NULL
     OR length(p_request_key) NOT BETWEEN 1 AND 200
     OR p_occurrences IS NULL OR jsonb_typeof(p_occurrences) <> 'array'
     OR jsonb_array_length(p_occurrences) NOT BETWEEN 1 AND 450 THEN
    RAISE EXCEPTION 'invalid_request' USING ERRCODE='P0001';
  END IF;
  SELECT access::text, CASE WHEN plan_tier='plus' THEN 'pro' ELSE plan_tier END
    INTO v_access,v_tier FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001'; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.profiles WHERE id=p_profile_id AND user_id=p_user_id) THEN
    RAISE EXCEPTION 'profile_not_owned' USING ERRCODE='P0001';
  END IF;
  v_payload := jsonb_build_object('profile_id',p_profile_id,'draft_id',p_draft_id,
                                   'revision',p_revision,'occurrences',p_occurrences);
  SELECT id,request_payload INTO v_id,v_old FROM public.campaign_reservations_f4e
    WHERE user_id=p_user_id AND request_key=p_request_key;
  IF FOUND THEN
    IF v_old IS DISTINCT FROM v_payload THEN
      RAISE EXCEPTION 'idempotency_conflict' USING ERRCODE='P0001';
    END IF;
    RETURN v_id;
  END IF;
  SELECT to_jsonb(d) INTO v_draft FROM public.campaign_drafts d
    WHERE d.id=p_draft_id AND d.user_id=p_user_id AND d.profile_id=p_profile_id
      AND d.status='draft' AND d.revision=p_revision FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'draft_not_owned_or_revision_mismatch' USING ERRCODE='P0001'; END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_occurrences) x
             WHERE jsonb_typeof(x) <> 'string') THEN
    RAISE EXCEPTION 'invalid_occurrences' USING ERRCODE='P0001';
  END IF;
  IF v_access IS DISTINCT FROM 'ADMIN' THEN
    SELECT active_campaigns_per_profile INTO v_limit FROM public.plan_limits WHERE tier=v_tier;
    IF v_limit IS NULL THEN RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001'; END IF;
    IF (SELECT count(*) FROM public.campaign_reservations_f4e
        WHERE user_id=p_user_id AND profile_id=p_profile_id AND status='reserved_no_dispatch') >= v_limit THEN
      RAISE EXCEPTION 'campaign_quota_exceeded' USING ERRCODE='P0001';
    END IF;
  END IF;
  IF EXISTS (SELECT 1 FROM public.campaign_draft_media
             WHERE campaign_id=p_draft_id AND status <> 'ready') THEN
    RAISE EXCEPTION 'media_not_ready' USING ERRCODE='P0001';
  END IF;
  SELECT COALESCE(jsonb_agg(to_jsonb(m) ORDER BY m.product_id,m.slot),'[]'::jsonb)
    INTO v_media FROM public.campaign_draft_media m
    WHERE m.campaign_id=p_draft_id AND m.user_id=p_user_id AND m.profile_id=p_profile_id;
  INSERT INTO public.campaign_reservations_f4e
    (user_id,profile_id,draft_id,request_key,request_payload,draft_snapshot,media_snapshot)
    VALUES (p_user_id,p_profile_id,p_draft_id,p_request_key,v_payload,v_draft,v_media)
    RETURNING id INTO v_id;
  INSERT INTO public.campaign_occurrences_f4e(reservation_id,ordinal,planned_at)
    SELECT v_id, ord::integer, (value #>> '{}')::timestamptz
    FROM jsonb_array_elements(p_occurrences) WITH ORDINALITY AS a(value,ord);
  RETURN v_id;
END; $$;

CREATE FUNCTION public.release_campaign_f4e(p_user_id uuid,p_profile_id uuid,p_reservation_id uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
  PERFORM 1 FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND OR NOT EXISTS (SELECT 1 FROM public.profiles
      WHERE id=p_profile_id AND user_id=p_user_id) THEN
    RAISE EXCEPTION 'account_or_profile_not_owned' USING ERRCODE='P0001';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.campaign_reservations_f4e
      WHERE id=p_reservation_id AND user_id=p_user_id AND profile_id=p_profile_id) THEN
    RAISE EXCEPTION 'reservation_not_owned' USING ERRCODE='P0001';
  END IF;
  UPDATE public.campaign_occurrences_f4e SET status='cancelled'
    WHERE reservation_id=p_reservation_id AND status='planned';
  UPDATE public.campaign_reservations_f4e SET status='released',released_at=now()
    WHERE id=p_reservation_id AND status='reserved_no_dispatch';
  RETURN true;
END; $$;
REVOKE ALL ON FUNCTION public.reserve_campaign_f4e(uuid,uuid,uuid,integer,text,jsonb)
  FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.release_campaign_f4e(uuid,uuid,uuid)
  FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.reserve_campaign_f4e(uuid,uuid,uuid,integer,text,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_campaign_f4e(uuid,uuid,uuid) TO service_role;
COMMIT;

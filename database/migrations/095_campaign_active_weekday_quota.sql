-- Campaign quota counts only scheduled weekdays, not every calendar date.
-- Additive replacement of the atomic reservation guard; no table/data changes.
BEGIN;
SET LOCAL lock_timeout = '10s';

CREATE OR REPLACE FUNCTION public.reserve_campaign_f4e(
  p_user_id uuid, p_profile_id uuid, p_draft_id uuid,
  p_revision integer, p_request_key text, p_occurrences jsonb
) RETURNS uuid LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_access text; v_tier text; v_limit integer; v_id uuid;
  v_payload jsonb; v_old jsonb; v_draft jsonb; v_media jsonb;
  v_days integer; v_day_cap integer; v_start date; v_end date;
  v_weekdays jsonb; v_active_days integer;
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
  IF v_access NOT IN ('USER','ADMIN') OR v_access IS NULL
     OR v_tier NOT IN ('free','pro','premium') OR v_tier IS NULL THEN
    RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001';
  END IF;
  IF v_access = 'ADMIN' THEN
    v_days := 30; v_day_cap := NULL;
  ELSE
    SELECT active_campaigns_per_profile, LEAST(campaign_days,30), campaign_posts_per_day
      INTO v_limit,v_days,v_day_cap FROM public.plan_limits WHERE tier=v_tier;
    IF v_limit IS NULL OR v_days IS NULL OR v_day_cap IS NULL OR v_days < 1 OR v_day_cap < 1 THEN
      RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001'; END IF;
    IF (SELECT count(*) FROM public.campaign_reservations_f4e
        WHERE user_id=p_user_id AND profile_id=p_profile_id AND status='reserved_no_dispatch') >= v_limit THEN
      RAISE EXCEPTION 'campaign_quota_exceeded' USING ERRCODE='P0001';
    END IF;
  END IF;
  -- UTC explicito; nao e um payload de publicacao.
  IF EXISTS (SELECT 1 FROM jsonb_array_elements_text(p_occurrences) x
             WHERE x !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$') THEN
    RAISE EXCEPTION 'timestamps_require_utc_z' USING ERRCODE='P0001';
  END IF;
  IF (v_draft->'schedule'->>'start_date') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     OR (v_draft->'schedule'->>'end_date') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     OR v_draft->'schedule'->>'start_date' IS NULL
     OR v_draft->'schedule'->>'end_date' IS NULL THEN
    RAISE EXCEPTION 'invalid_schedule_dates' USING ERRCODE='P0001';
  END IF;
  v_start := (v_draft->'schedule'->>'start_date')::date;
  v_end := (v_draft->'schedule'->>'end_date')::date;
  v_weekdays := v_draft->'schedule'->'weekdays';
  IF jsonb_typeof(v_weekdays) IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION 'invalid_campaign_weekdays' USING ERRCODE='P0001';
  END IF;
  IF jsonb_array_length(v_weekdays) NOT BETWEEN 1 AND 7 THEN
    RAISE EXCEPTION 'invalid_campaign_weekdays' USING ERRCODE='P0001';
  END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_array_elements_text(v_weekdays) AS weekday(value)
    WHERE COALESCE(weekday.value,'') !~ '^[0-6]$'
  ) THEN
    RAISE EXCEPTION 'invalid_campaign_weekdays' USING ERRCODE='P0001';
  END IF;
  -- A campaign may span up to 210 calendar days, but only selected weekdays
  -- consume the plan's maximum of 30 active publication days.
  IF v_end < v_start OR v_end-v_start+1 > 210 THEN
    RAISE EXCEPTION 'campaign_window_exceeded' USING ERRCODE='P0001';
  END IF;
  SELECT count(*) INTO v_active_days
  FROM generate_series(v_start::timestamp, v_end::timestamp, interval '1 day') AS day_value(day_at)
  WHERE EXISTS (
    SELECT 1 FROM jsonb_array_elements_text(v_weekdays) AS weekday(value)
    WHERE weekday.value::integer = EXTRACT(ISODOW FROM day_value.day_at)::integer - 1
  );
  IF v_active_days < 1 OR v_active_days > v_days THEN
    RAISE EXCEPTION 'campaign_active_days_exceeded' USING ERRCODE='P0001';
  END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements_text(p_occurrences) x
             WHERE x::timestamptz <= now()
                OR (x::timestamptz AT TIME ZONE 'America/Sao_Paulo')::date NOT BETWEEN v_start AND v_end
                OR NOT EXISTS (
                  SELECT 1 FROM jsonb_array_elements_text(v_weekdays) AS weekday(value)
                  WHERE weekday.value::integer =
                    EXTRACT(ISODOW FROM (x::timestamptz AT TIME ZONE 'America/Sao_Paulo'))::integer - 1
                ))
     OR (SELECT count(*) FROM jsonb_array_elements_text(p_occurrences))
        <> (SELECT count(DISTINCT x::timestamptz) FROM jsonb_array_elements_text(p_occurrences) x) THEN
    RAISE EXCEPTION 'invalid_occurrences' USING ERRCODE='P0001';
  END IF;
  -- Conta slots, nao redes; validacao de rede por produto continua bloqueante.
  IF v_day_cap IS NOT NULL AND EXISTS (
      SELECT 1 FROM jsonb_array_elements_text(p_occurrences) x
      GROUP BY (x::timestamptz AT TIME ZONE 'America/Sao_Paulo')::date
      HAVING count(*) > v_day_cap) THEN
    RAISE EXCEPTION 'campaign_day_slots_exceeded' USING ERRCODE='P0001';
  END IF;
  -- O lock de draft bloqueia inserts com FK imediata; trava as midias existentes.
  PERFORM 1 FROM public.campaign_draft_media WHERE campaign_id=p_draft_id FOR UPDATE;
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

REVOKE ALL ON FUNCTION public.reserve_campaign_f4e(uuid,uuid,uuid,integer,text,jsonb)
  FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.reserve_campaign_f4e(uuid,uuid,uuid,integer,text,jsonb)
  TO service_role;

COMMIT;

-- F4E3: dedicated network-aware worker, independent from legacy queue.
BEGIN;
SET LOCAL lock_timeout='5s';

CREATE FUNCTION public.claim_campaign_publication_f4e(p_environment text,p_worker text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_slot record; v_res record; v_token uuid; v_job record;
BEGIN
 IF p_environment NOT IN ('staging','production') OR length(p_worker) NOT BETWEEN 1 AND 150
 THEN RAISE EXCEPTION 'invalid_worker' USING ERRCODE='P0001'; END IF;
 SELECT s.* INTO v_slot
 FROM public.campaign_network_slots_f4e s
 JOIN public.campaign_reservations_f4e r ON r.id=s.reservation_id
 JOIN public.publish_jobs j ON j.id=s.publish_job_id
 JOIN public.users u ON u.id=r.user_id
 WHERE s.source_environment=p_environment
  AND r.source_environment=p_environment
  AND r.lifecycle='active' AND r.dispatch_enabled
  AND r.status='reserved_no_dispatch'
  AND s.state='planned'
  AND s.planned_at<=now() AND s.planned_at>now()-interval '1 hour'
  AND j.status='pending' AND j.publication_origin='campaign'
  AND (u.access::text='ADMIN'
    OR (u.plan_tier IN ('pro','plus','premium') AND u.campaign_paid_through>now()))
 ORDER BY s.planned_at,s.id LIMIT 1 FOR UPDATE OF s SKIP LOCKED;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO v_res FROM public.campaign_reservations_f4e
  WHERE id=v_slot.reservation_id FOR UPDATE;
 IF v_res.lifecycle<>'active' OR NOT v_res.dispatch_enabled
 THEN RETURN NULL; END IF;
 SELECT * INTO v_job FROM public.publish_jobs
  WHERE id=v_slot.publish_job_id AND status='pending' AND publication_origin='campaign'
  FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 v_token:=gen_random_uuid();
 UPDATE public.campaign_network_slots_f4e SET state='running' WHERE id=v_slot.id;
 UPDATE public.publish_jobs SET status='running',attempt=attempt+1,claim_token=v_token,
  preflight_claim_token=v_token,locked_by=p_worker,locked_at=now(),
  started_at=COALESCE(started_at,now()),scheduled_for=v_slot.planned_at
 WHERE id=v_job.id;
 RETURN jsonb_build_object('publish_job_id',v_job.id,'scheduler_id',v_job.scheduler_id,
  'claim_token',v_token,'network',v_slot.network,'user_id',v_slot.user_id,'profile_id',v_slot.profile_id);
END; $$;

CREATE FUNCTION public.mark_campaign_external_f4e(
 p_environment text,p_job uuid,p_token uuid
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_res uuid; v_owner record; v_state record;
BEGIN
 SELECT s.reservation_id INTO v_res FROM public.campaign_network_slots_f4e s
 JOIN public.publish_jobs j ON j.id=s.publish_job_id
 WHERE j.id=p_job AND j.claim_token=p_token AND j.status='running'
  AND j.preflight_claim_token=p_token
  AND s.state='running' AND s.source_environment=p_environment;
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT r.*,u.access::text AS user_access,u.plan_tier AS current_tier,
  u.campaign_paid_through AS paid_through
 INTO v_state FROM public.campaign_reservations_f4e r
 JOIN public.users u ON u.id=r.user_id
 WHERE r.id=v_res FOR UPDATE OF r;
 IF v_state.lifecycle<>'active' OR NOT v_state.dispatch_enabled
  OR v_state.source_environment<>p_environment
  OR (v_state.user_access<>'ADMIN' AND
    (v_state.current_tier NOT IN ('pro','plus','premium')
     OR v_state.paid_through<=now() OR v_state.paid_through IS NULL))
 THEN RETURN false; END IF;
 UPDATE public.publish_jobs SET external_started_at=COALESCE(external_started_at,now())
 WHERE id=p_job AND claim_token=p_token AND preflight_claim_token=p_token
  AND status='running' AND publication_origin='campaign'
  AND EXISTS (
    SELECT 1 FROM public.campaign_network_slots_f4e s
    JOIN public.campaign_reservations_f4e r ON r.id=s.reservation_id
    JOIN public.users u ON u.id=r.user_id
    WHERE s.publish_job_id=p_job AND s.state='running'
      AND s.source_environment=p_environment
      AND r.lifecycle='active' AND r.dispatch_enabled
      AND r.status='reserved_no_dispatch'
      AND r.source_environment=p_environment
      AND (u.access::text='ADMIN' OR
        (u.plan_tier IN ('pro','plus','premium')
         AND u.campaign_paid_through>now()))
  );
 RETURN FOUND;
END; $$;

CREATE FUNCTION public.finish_campaign_publication_f4e(
 p_environment text,p_job uuid,p_token uuid,p_status text,
 p_external text DEFAULT NULL,p_error text DEFAULT NULL
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_slot uuid;
BEGIN
 IF p_status NOT IN ('succeeded','failed','unknown')
 THEN RAISE EXCEPTION 'invalid_terminal_state' USING ERRCODE='P0001'; END IF;
 SELECT s.id INTO v_slot FROM public.campaign_network_slots_f4e s
 JOIN public.publish_jobs j ON j.id=s.publish_job_id
 WHERE j.id=p_job AND j.status='running' AND j.claim_token=p_token
  AND s.source_environment=p_environment
 FOR UPDATE OF s;
 IF NOT FOUND THEN RETURN false; END IF;
 UPDATE public.publish_jobs SET status=p_status,external_id=left(p_external,500),
   last_error=left(p_error,2000),finished_at=now(),
   claim_token=NULL,locked_by=NULL,locked_at=NULL
 WHERE id=p_job AND claim_token=p_token AND publication_origin='campaign';
 IF NOT FOUND THEN RETURN false; END IF;
 UPDATE public.campaign_network_slots_f4e SET state=p_status,finished_at=now()
 WHERE id=v_slot;
 RETURN true;
END; $$;

CREATE FUNCTION public.recover_campaign_publications_f4e(p_environment text)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_job record; v_result integer:=0; v_next text;
BEGIN
 IF p_environment NOT IN ('staging','production')
 THEN RAISE EXCEPTION 'invalid_environment' USING ERRCODE='P0001'; END IF;
 -- In-memory worker loss: never replay when external interaction may have occurred.
 FOR v_job IN
  SELECT j.*,s.id AS slot_id,s.planned_at,r.lifecycle
  FROM public.publish_jobs j
  JOIN public.campaign_network_slots_f4e s ON s.publish_job_id=j.id
  JOIN public.campaign_reservations_f4e r ON r.id=s.reservation_id
  WHERE j.publication_origin='campaign' AND s.source_environment=p_environment
    AND (
      (j.status='running' AND j.locked_at<now()-interval '5 minutes')
      OR (j.status='pending' AND s.planned_at<now()-interval '1 hour')
    )
  ORDER BY s.planned_at LIMIT 100 FOR UPDATE OF j SKIP LOCKED
 LOOP
  IF v_job.status='pending' THEN
    UPDATE public.publish_jobs SET status='failed',
      last_error='Horário de campanha expirado sem publicação',finished_at=now()
    WHERE id=v_job.id;
    v_next:='failed';
  ELSIF v_job.external_started_at IS NOT NULL THEN
    UPDATE public.publish_jobs SET status='unknown',
      last_error='Envio iniciado; resultado incerto, sem repetição automática',
      finished_at=now(),claim_token=NULL,locked_by=NULL,locked_at=NULL
    WHERE id=v_job.id;
    v_next:='unknown';
  ELSIF v_job.attempt>=3 OR v_job.planned_at<now()-interval '1 hour' THEN
    UPDATE public.publish_jobs SET status='failed',
      last_error='Tentativas de preparação esgotadas ou janela expirada',
      finished_at=now(),claim_token=NULL,locked_by=NULL,locked_at=NULL
    WHERE id=v_job.id;
    v_next:='failed';
  ELSE
    UPDATE public.publish_jobs SET status='pending',claim_token=NULL,
     preflight_claim_token=NULL,locked_by=NULL,locked_at=NULL,
     last_error='Preparação retomada antes de contato externo'
    WHERE id=v_job.id;
    v_next:='planned';
  END IF;
  UPDATE public.campaign_network_slots_f4e SET state=v_next,
   finished_at=CASE WHEN v_next='planned' THEN NULL ELSE now() END
  WHERE id=v_job.slot_id;
  v_result:=v_result+1;
 END LOOP;
 RETURN v_result;
END; $$;

-- Commercial period expiry: fail closed without changing the user's paid plan.
CREATE FUNCTION public.pause_expired_campaigns_f4e(p_environment text)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_res record; v_n integer:=0;
BEGIN
 -- A pending downgrade never changes entitlements before its paid boundary.
 IF p_environment='production' THEN
  UPDATE public.users u SET plan_tier=u.campaign_pending_tier,
    campaign_pending_tier=NULL,campaign_tier_effective_at=NULL
  WHERE u.campaign_pending_tier IS NOT NULL
    AND u.campaign_tier_effective_at<=now()
    AND (u.campaign_paid_through IS NULL OR u.campaign_paid_through<=now());
 END IF;
 FOR v_res IN SELECT r.id FROM public.campaign_reservations_f4e r
 JOIN public.users u ON u.id=r.user_id
 WHERE r.lifecycle='active' AND r.source_environment=p_environment
 AND u.access::text<>'ADMIN' AND
 (u.campaign_paid_through IS NULL OR u.campaign_paid_through<=now()
  OR u.plan_tier NOT IN ('pro','plus','premium'))
 ORDER BY r.id LIMIT 100 FOR UPDATE OF r SKIP LOCKED
 LOOP
  UPDATE public.campaign_reservations_f4e SET lifecycle='paused',
   dispatch_enabled=false,pause_reason='paid_period_expired' WHERE id=v_res.id;
  UPDATE public.campaign_occurrences_f4e SET dispatch_enabled=false
   WHERE reservation_id=v_res.id AND status='planned';
  v_n:=v_n+1;
 END LOOP;
 RETURN v_n;
END; $$;

CREATE FUNCTION public.close_completed_campaigns_f4e(p_environment text)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_res record; v_n integer:=0;
BEGIN
 FOR v_res IN SELECT r.id FROM public.campaign_reservations_f4e r
 WHERE r.source_environment=p_environment AND r.lifecycle IN ('active','paused')
  AND EXISTS (SELECT 1 FROM public.campaign_network_slots_f4e s WHERE s.reservation_id=r.id)
  AND NOT EXISTS (SELECT 1 FROM public.campaign_network_slots_f4e s
   WHERE s.reservation_id=r.id AND s.state IN ('planned','running'))
 ORDER BY r.id LIMIT 100 FOR UPDATE OF r SKIP LOCKED
 LOOP
  UPDATE public.campaign_reservations_f4e SET lifecycle='completed',
   status='released',released_at=now(),dispatch_enabled=false
   WHERE id=v_res.id;
  UPDATE public.campaign_occurrences_f4e SET dispatch_enabled=false
   WHERE reservation_id=v_res.id;
  v_n:=v_n+1;
 END LOOP;
 RETURN v_n;
END; $$;

REVOKE ALL ON FUNCTION public.close_completed_campaigns_f4e(text)
 FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.close_completed_campaigns_f4e(text) TO service_role;

REVOKE ALL ON FUNCTION public.claim_campaign_publication_f4e(text,text) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.mark_campaign_external_f4e(text,uuid,uuid) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.finish_campaign_publication_f4e(text,uuid,uuid,text,text,text) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.recover_campaign_publications_f4e(text) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.pause_expired_campaigns_f4e(text) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.claim_campaign_publication_f4e(text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.mark_campaign_external_f4e(text,uuid,uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.finish_campaign_publication_f4e(text,uuid,uuid,text,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.recover_campaign_publications_f4e(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.pause_expired_campaigns_f4e(text) TO service_role;
COMMIT;

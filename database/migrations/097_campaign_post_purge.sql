-- Apagar posts de campanha que nunca rodaram (pedido do dono do produto) e limpar os posts de uma
-- campanha cancelada. A trava `campaign_job_immutable` impede apagar o post com a vaga ainda ligada
-- ao job, então a vaga sai primeiro (sem trigger de DELETE) e depois o post (CASCADE em agendador,
-- job, mídia e produto). Vagas já executadas (succeeded/failed/unknown) ficam: são histórico e
-- contam na cota diária do plano; vaga em envio (running) não é interrompida.
CREATE OR REPLACE FUNCTION public.purge_campaign_posts_f4e(
  p_user_id uuid, p_profile_id uuid, p_post_ids integer[]
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_count integer;
BEGIN
  IF p_post_ids IS NULL OR cardinality(p_post_ids)=0 THEN RETURN 0; END IF;
  PERFORM 1 FROM public.campaign_network_slots_f4e s
    WHERE s.post_id=ANY(p_post_ids) AND s.user_id=p_user_id AND s.profile_id=p_profile_id
    FOR UPDATE;
  IF EXISTS (SELECT 1 FROM public.campaign_network_slots_f4e s
      WHERE s.post_id=ANY(p_post_ids) AND s.user_id=p_user_id AND s.profile_id=p_profile_id
        AND s.state='running') THEN
    RAISE EXCEPTION 'campaign_post_running' USING ERRCODE='P0001';
  END IF;
  IF EXISTS (SELECT 1 FROM public.campaign_network_slots_f4e s
      WHERE s.post_id=ANY(p_post_ids) AND s.user_id=p_user_id AND s.profile_id=p_profile_id
        AND s.state IN ('succeeded','failed','unknown')) THEN
    RAISE EXCEPTION 'campaign_post_has_history' USING ERRCODE='P0001';
  END IF;
  DELETE FROM public.campaign_network_slots_f4e s
    WHERE s.post_id=ANY(p_post_ids) AND s.user_id=p_user_id AND s.profile_id=p_profile_id
      AND s.state IN ('planned','cancelled');
  DELETE FROM public.posts p
    WHERE p.id=ANY(p_post_ids) AND p.user_id=p_user_id AND p.profile_id=p_profile_id
      AND p.publication_origin='campaign';
  GET DIAGNOSTICS v_count=ROW_COUNT;
  RETURN v_count;
END; $$;

-- Depois de cancelar: apaga os posts das vagas canceladas antes do disparo. O que já foi
-- publicado ou falhou fica no histórico da campanha.
CREATE OR REPLACE FUNCTION public.purge_cancelled_campaign_f4e(
  p_user_id uuid, p_profile_id uuid, p_reservation_id uuid
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE v_ids integer[];
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.campaign_reservations_f4e r
      WHERE r.id=p_reservation_id AND r.user_id=p_user_id AND r.profile_id=p_profile_id
        AND r.lifecycle='cancelled') THEN
    RAISE EXCEPTION 'campaign_not_cancelled' USING ERRCODE='P0001';
  END IF;
  SELECT array_agg(s.post_id) INTO v_ids
  FROM public.campaign_network_slots_f4e s
  WHERE s.reservation_id=p_reservation_id AND s.state='cancelled' AND s.post_id IS NOT NULL;
  RETURN public.purge_campaign_posts_f4e(p_user_id,p_profile_id,COALESCE(v_ids,ARRAY[]::integer[]));
END; $$;

REVOKE ALL ON FUNCTION public.purge_campaign_posts_f4e(uuid,uuid,integer[])
  FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.purge_cancelled_campaign_f4e(uuid,uuid,uuid)
  FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.purge_campaign_posts_f4e(uuid,uuid,integer[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.purge_cancelled_campaign_f4e(uuid,uuid,uuid) TO service_role;

-- F4E: materializacao transacional por rede/dia, sem alterar filas legadas.
-- Deploy de schema aditivo; produtores permanecem bloqueados ate todos os testes.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE public.users
  ADD COLUMN campaign_paid_through timestamptz,
  ADD COLUMN campaign_pending_tier text,
  ADD COLUMN campaign_tier_effective_at timestamptz;
ALTER TABLE public.users
  ADD CONSTRAINT users_campaign_pending_tier_valid
  CHECK (campaign_pending_tier IS NULL OR campaign_pending_tier IN ('free','pro','premium'));
ALTER TABLE public.users
  ADD CONSTRAINT users_campaign_transition_valid
  CHECK ((campaign_pending_tier IS NULL) = (campaign_tier_effective_at IS NULL));

ALTER TABLE public.campaign_reservations_f4e
  ADD COLUMN lifecycle text NOT NULL DEFAULT 'preparing'
    CHECK (lifecycle IN ('preparing','active','paused','cancelled','completed')),
  ADD COLUMN activated_at timestamptz,
  ADD COLUMN pause_reason text,
  ADD COLUMN source_environment text
    CHECK (source_environment IN ('production','staging')),
  ADD COLUMN media_verified_at timestamptz,
  ADD COLUMN oauth_verified_at timestamptz;
ALTER TABLE public.campaign_reservations_f4e
  ADD CONSTRAINT campaign_activation_state_consistent
  CHECK (lifecycle <> 'active' OR (activated_at IS NOT NULL
         AND media_verified_at IS NOT NULL AND oauth_verified_at IS NOT NULL
         AND source_environment IS NOT NULL));

CREATE TABLE public.campaign_network_slots_f4e (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reservation_id uuid NOT NULL REFERENCES public.campaign_reservations_f4e(id) ON DELETE CASCADE,
  occurrence_id uuid NOT NULL REFERENCES public.campaign_occurrences_f4e(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  product_id integer NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
  network text NOT NULL CHECK (network IN ('threads','x','facebook','instagram','tiktok')),
  planned_at timestamptz NOT NULL,
  content_text text NOT NULL,
  media_snapshot jsonb NOT NULL DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(media_snapshot) = 'array'),
  state text NOT NULL DEFAULT 'planned'
    CHECK (state IN ('planned','running','succeeded','failed','unknown','cancelled')),
  post_id integer REFERENCES public.posts(id) ON DELETE SET NULL,
  scheduler_id uuid REFERENCES public.schedulers(id) ON DELETE SET NULL,
  publish_job_id uuid REFERENCES public.publish_jobs(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  UNIQUE (occurrence_id, network),
  UNIQUE (publish_job_id),
  UNIQUE (scheduler_id),
  UNIQUE (post_id)
);
CREATE INDEX campaign_network_slots_owner_day_idx
  ON public.campaign_network_slots_f4e(user_id, profile_id, planned_at)
  WHERE state <> 'cancelled';
CREATE INDEX campaign_network_slots_due_idx
  ON public.campaign_network_slots_f4e(planned_at, state)
  WHERE state IN ('planned','running');
CREATE INDEX campaign_network_slots_reservation_idx
  ON public.campaign_network_slots_f4e(reservation_id);

ALTER TABLE public.campaign_network_slots_f4e ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.campaign_network_slots_f4e FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT ON TABLE public.campaign_network_slots_f4e TO service_role;
GRANT UPDATE (state, post_id, scheduler_id, publish_job_id, finished_at)
  ON TABLE public.campaign_network_slots_f4e TO service_role;

CREATE FUNCTION public.guard_campaign_network_slot_f4e()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE
  v_user uuid; v_profile uuid; v_time timestamptz;
  v_draft jsonb; v_item jsonb;
BEGIN
  SELECT r.user_id, r.profile_id, o.planned_at, r.draft_snapshot
  INTO v_user, v_profile, v_time, v_draft
  FROM public.campaign_reservations_f4e r
  JOIN public.campaign_occurrences_f4e o ON o.reservation_id=r.id
  WHERE r.id=NEW.reservation_id AND o.id=NEW.occurrence_id;
  IF v_user IS NULL OR NEW.user_id IS DISTINCT FROM v_user
     OR NEW.profile_id IS DISTINCT FROM v_profile
     OR NEW.planned_at IS DISTINCT FROM v_time THEN
    RAISE EXCEPTION 'campaign_slot_identity_mismatch' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' THEN
    IF ROW(NEW.reservation_id, NEW.occurrence_id, NEW.user_id, NEW.profile_id,
           NEW.product_id, NEW.network, NEW.planned_at, NEW.content_text, NEW.media_snapshot)
       IS DISTINCT FROM
       ROW(OLD.reservation_id, OLD.occurrence_id, OLD.user_id, OLD.profile_id,
           OLD.product_id, OLD.network, OLD.planned_at, OLD.content_text, OLD.media_snapshot) THEN
      RAISE EXCEPTION 'campaign_slot_immutable' USING ERRCODE='23514';
    END IF;
    IF OLD.state IN ('succeeded','failed','unknown','cancelled')
       AND NEW.state IS DISTINCT FROM OLD.state THEN
      RAISE EXCEPTION 'campaign_slot_terminal' USING ERRCODE='23514';
    END IF;
    IF OLD.publish_job_id IS NOT NULL
       AND NEW.publish_job_id IS DISTINCT FROM OLD.publish_job_id THEN
      RAISE EXCEPTION 'campaign_job_immutable' USING ERRCODE='23514';
    END IF;
  ELSE
    SELECT item INTO v_item FROM jsonb_array_elements(v_draft->'items') item
    WHERE (item->>'product_id')::integer=NEW.product_id;
    IF v_item IS NULL
       OR NOT (v_item->'networks' ? NEW.network) THEN
      -- jsonb array de strings nao suporta o operador ? para comparacao segura
      IF v_item IS NULL OR NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements_text(v_item->'networks') n WHERE n=NEW.network
      ) THEN
        RAISE EXCEPTION 'campaign_network_not_in_draft' USING ERRCODE='23514';
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END; $$;
REVOKE ALL ON FUNCTION public.guard_campaign_network_slot_f4e()
  FROM PUBLIC,anon,authenticated,service_role;
CREATE TRIGGER trg_guard_campaign_network_slot_f4e
  BEFORE INSERT OR UPDATE ON public.campaign_network_slots_f4e
  FOR EACH ROW EXECUTE FUNCTION public.guard_campaign_network_slot_f4e();

-- A linha de users serializa ativacoes concorrentes em todos os perfis da conta.
-- V1 permanece disponivel apenas para a prova historica, nao para runtime.
REVOKE EXECUTE ON FUNCTION public.reserve_campaign_f4e(uuid,uuid,uuid,integer,text,jsonb)
  FROM service_role;

CREATE FUNCTION public.reserve_campaign_networks_f4e(
  p_user_id uuid, p_profile_id uuid, p_draft_id uuid,
  p_revision integer, p_request_key text, p_occurrences jsonb
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE
  v_reservation uuid; v_snapshot jsonb; v_media jsonb;
  v_access text; v_tier text; v_daily_limit integer; v_start date; v_end date;
  v_total integer;
BEGIN
  IF p_user_id IS NULL OR p_profile_id IS NULL OR p_draft_id IS NULL
     OR p_revision IS NULL OR p_revision < 1 OR p_request_key IS NULL
     OR length(p_request_key) NOT BETWEEN 1 AND 200 THEN
    RAISE EXCEPTION 'invalid_campaign_request' USING ERRCODE='P0001';
  END IF;
  SELECT u.access::text, CASE WHEN u.plan_tier='plus' THEN 'pro' ELSE u.plan_tier END
  INTO v_access, v_tier FROM public.users u WHERE u.id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001'; END IF;
  -- Pago ate o instante efetivo; pedido pendente nao reduz direitos.
  IF v_access <> 'ADMIN' AND NOT EXISTS (
    SELECT 1 FROM public.users u
    WHERE u.id=p_user_id AND u.campaign_paid_through > now()
  ) THEN RAISE EXCEPTION 'paid_period_not_confirmed' USING ERRCODE='P0001'; END IF;

  -- A RPC antiga valida janela, ownership, idempotencia, limites de
  -- campanhas e faz snapshot de midias e ocorrencias no MESMO commit.
  v_reservation := public.reserve_campaign_f4e(
    p_user_id,p_profile_id,p_draft_id,p_revision,p_request_key,p_occurrences);
  SELECT r.draft_snapshot,r.media_snapshot INTO v_snapshot,v_media
  FROM public.campaign_reservations_f4e r WHERE r.id=v_reservation FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'reservation_missing' USING ERRCODE='P0001'; END IF;

  IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_snapshot->'items') item
             WHERE jsonb_typeof(item->'networks') <> 'array'
                OR jsonb_array_length(item->'networks') = 0
                OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(item->'networks') n
                           WHERE n NOT IN ('threads','x','facebook','instagram','tiktok')))
  THEN RAISE EXCEPTION 'invalid_campaign_network' USING ERRCODE='P0001'; END IF;

  IF NOT EXISTS (SELECT 1 FROM public.campaign_network_slots_f4e
                 WHERE reservation_id=v_reservation) THEN
    INSERT INTO public.campaign_network_slots_f4e
      (reservation_id,occurrence_id,user_id,profile_id,product_id,network,
       planned_at,content_text,media_snapshot)
    SELECT v_reservation,o.id,p_user_id,p_profile_id,
           (item->>'product_id')::integer, network.value,o.planned_at,
           COALESCE(NULLIF(item->'network_copies'->>network.value,''),
                    item->>'copy',''),
           COALESCE((
             SELECT jsonb_agg(media ORDER BY (media->>'slot')::integer)
             FROM jsonb_array_elements(v_media) media
             WHERE (media->>'product_id')::integer=(item->>'product_id')::integer
           ),'[]'::jsonb)
    FROM public.campaign_occurrences_f4e o
    CROSS JOIN LATERAL (
      SELECT v_snapshot->'items'->(((o.ordinal-1) %
        jsonb_array_length(v_snapshot->'items'))::integer) AS item
    ) ordered_item
    CROSS JOIN LATERAL jsonb_array_elements_text(item->'networks') AS network(value)
    WHERE o.reservation_id=v_reservation;
  END IF;

  SELECT CASE WHEN v_access='ADMIN' THEN NULL ELSE campaign_posts_per_day END
  INTO v_daily_limit FROM public.plan_limits WHERE tier=v_tier;
  IF v_access <> 'ADMIN' AND (v_daily_limit IS NULL OR v_daily_limit < 1)
  THEN RAISE EXCEPTION 'plan_limits_unavailable' USING ERRCODE='P0001'; END IF;

  -- Cota compartilhada entre campanhas do mesmo perfil: 1 rede = 1 unidade.
  IF v_daily_limit IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.campaign_network_slots_f4e s
    JOIN public.campaign_reservations_f4e r ON r.id=s.reservation_id
    WHERE s.user_id=p_user_id AND s.profile_id=p_profile_id
      AND r.status='reserved_no_dispatch' AND s.state <> 'cancelled'
    GROUP BY (s.planned_at AT TIME ZONE 'America/Sao_Paulo')::date
    HAVING count(*) > v_daily_limit
  ) THEN RAISE EXCEPTION 'campaign_network_day_quota_exceeded' USING ERRCODE='P0001'; END IF;

  RETURN v_reservation;
END; $$;
REVOKE ALL ON FUNCTION public.reserve_campaign_networks_f4e(uuid,uuid,uuid,integer,text,jsonb)
  FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.reserve_campaign_networks_f4e(uuid,uuid,uuid,integer,text,jsonb)
  TO service_role;

-- Runtime e terminalidade ficam separados de "status" da reserva historica;
-- nenhum worker legado tem autorizacao derivada da ausencia de vinculo.
ALTER TABLE public.campaign_reservations_f4e
  DROP CONSTRAINT campaign_reservations_f4e_dispatch_enabled_check;
ALTER TABLE public.campaign_reservations_f4e
  ADD CONSTRAINT campaign_reservation_dispatch_state
  CHECK (dispatch_enabled = (lifecycle='active'));
ALTER TABLE public.campaign_occurrences_f4e
  DROP CONSTRAINT campaign_occurrences_f4e_dispatch_enabled_check;

ALTER TABLE public.campaign_network_slots_f4e
  ADD COLUMN source_environment text CHECK (source_environment IN ('production','staging'));
GRANT UPDATE (source_environment) ON public.campaign_network_slots_f4e TO service_role;

-- Verificacao de ultima milha feita no banco, inclusive quando o worker
-- tenta alterar o job diretamente. Link ausente nunca e interpretado como legado.
CREATE OR REPLACE FUNCTION public.guard_publication_origin_f4e()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE
  v_parent_origin text;
BEGIN
  IF TG_OP='UPDATE' AND NEW.publication_origin IS DISTINCT FROM OLD.publication_origin THEN
    RAISE EXCEPTION 'publication_origin_immutable' USING ERRCODE='23514';
  END IF;
  IF TG_TABLE_NAME='publish_jobs' THEN
    SELECT s.publication_origin INTO v_parent_origin
    FROM public.schedulers s WHERE s.id=NEW.scheduler_id FOR KEY SHARE;
    IF v_parent_origin IS NULL OR NEW.publication_origin IS DISTINCT FROM v_parent_origin THEN
      RAISE EXCEPTION 'publication_origin_parent_mismatch' USING ERRCODE='23514';
    END IF;
    IF NEW.publication_origin='campaign' AND (
      (NEW.status='running' AND (TG_OP='INSERT' OR OLD.status IS DISTINCT FROM 'running'))
      OR (NEW.external_started_at IS NOT NULL AND (TG_OP='INSERT' OR NEW.external_started_at IS DISTINCT FROM OLD.external_started_at))
    ) AND NOT EXISTS (
      SELECT 1
      FROM public.campaign_network_slots_f4e slot
      JOIN public.campaign_reservations_f4e reservation
        ON reservation.id=slot.reservation_id
      JOIN public.campaign_occurrences_f4e occurrence
        ON occurrence.id=slot.occurrence_id
       AND occurrence.reservation_id=reservation.id
      JOIN public.schedulers sched ON sched.id=NEW.scheduler_id
      JOIN public.users owner ON owner.id=NEW.user_id
      WHERE slot.publish_job_id=NEW.id
        AND slot.scheduler_id=NEW.scheduler_id
        AND slot.post_id=NEW.post_id
        AND slot.user_id=NEW.user_id AND slot.profile_id=NEW.profile_id
        AND slot.network=NEW.network
        AND slot.state='running'
        AND slot.source_environment=sched.environment
        AND occurrence.dispatch_enabled=true AND occurrence.status='planned'
        AND reservation.dispatch_enabled=true AND reservation.lifecycle='active'
        AND reservation.status='reserved_no_dispatch'
        AND reservation.user_id=NEW.user_id AND reservation.profile_id=NEW.profile_id
        AND reservation.source_environment=sched.environment
        AND sched.publication_origin='campaign'
        AND sched.dispatch_cancelled_at IS NULL
        AND sched.post_id=NEW.post_id AND sched.user_id=NEW.user_id
        AND sched.profile_id=NEW.profile_id
        AND (owner.access::text='ADMIN' OR (
          owner.plan_tier IN ('pro','premium','plus')
          AND owner.campaign_paid_through > now()
        ))
    ) THEN
      RAISE EXCEPTION 'campaign_dispatch_not_authorized' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END; $$;

CREATE FUNCTION public.activate_campaign_networks_f4e(
  p_user_id uuid,p_profile_id uuid,p_reservation_id uuid,p_environment text
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE
  v_owner record; v_reservation record;
BEGIN
  IF p_environment NOT IN ('staging','production') THEN
    RAISE EXCEPTION 'invalid_environment' USING ERRCODE='P0001';
  END IF;
  SELECT access::text AS access,plan_tier,campaign_paid_through
    INTO v_owner FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND OR (v_owner.access<>'ADMIN' AND
     (v_owner.plan_tier NOT IN ('pro','plus','premium')
      OR v_owner.campaign_paid_through IS NULL OR v_owner.campaign_paid_through<=now()))
  THEN RAISE EXCEPTION 'paid_period_not_confirmed' USING ERRCODE='P0001'; END IF;
  SELECT * INTO v_reservation FROM public.campaign_reservations_f4e
    WHERE id=p_reservation_id AND user_id=p_user_id AND profile_id=p_profile_id
    FOR UPDATE;
  IF NOT FOUND OR v_reservation.status <> 'reserved_no_dispatch'
     OR v_reservation.lifecycle <> 'preparing' THEN
    RAISE EXCEPTION 'campaign_not_preparing' USING ERRCODE='P0001';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.campaign_network_slots_f4e
                 WHERE reservation_id=p_reservation_id) THEN
    RAISE EXCEPTION 'no_campaign_network_slots' USING ERRCODE='P0001';
  END IF;
  IF EXISTS (SELECT 1 FROM public.campaign_occurrences_f4e
    WHERE reservation_id=p_reservation_id AND planned_at <= now()+interval '30 minutes')
  THEN RAISE EXCEPTION 'activation_too_close_to_dispatch' USING ERRCODE='P0001'; END IF;
  UPDATE public.campaign_reservations_f4e
  SET lifecycle='active',dispatch_enabled=true,activated_at=now(),
      media_verified_at=now(),oauth_verified_at=now(),source_environment=p_environment
  WHERE id=p_reservation_id;
  UPDATE public.campaign_occurrences_f4e SET dispatch_enabled=true
  WHERE reservation_id=p_reservation_id AND status='planned';
  UPDATE public.campaign_network_slots_f4e
  SET source_environment=p_environment WHERE reservation_id=p_reservation_id;
  RETURN true;
END; $$;

CREATE FUNCTION public.change_campaign_lifecycle_f4e(
  p_user_id uuid,p_profile_id uuid,p_reservation_id uuid,p_action text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE
  v_owner record; v_reservation record; v_state text;
BEGIN
  IF p_action NOT IN ('pause','resume','cancel') THEN
    RAISE EXCEPTION 'invalid_action' USING ERRCODE='P0001'; END IF;
  SELECT access::text AS access,plan_tier,campaign_paid_through
    INTO v_owner FROM public.users WHERE id=p_user_id FOR UPDATE;
  SELECT * INTO v_reservation FROM public.campaign_reservations_f4e
    WHERE id=p_reservation_id AND user_id=p_user_id AND profile_id=p_profile_id
    FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'campaign_not_owned' USING ERRCODE='P0001'; END IF;
  IF p_action='pause' AND v_reservation.lifecycle='active' THEN
    v_state:='paused';
  ELSIF p_action='cancel' AND v_reservation.lifecycle IN ('preparing','active','paused') THEN
    v_state:='cancelled';
  ELSIF p_action='resume' AND v_reservation.lifecycle='paused'
        AND (v_owner.access='ADMIN' OR
          (v_owner.plan_tier IN ('pro','plus','premium') AND v_owner.campaign_paid_through>now()))
  THEN
    v_state:='active';
  ELSE RAISE EXCEPTION 'invalid_campaign_transition' USING ERRCODE='P0001'; END IF;
  UPDATE public.campaign_reservations_f4e
  SET lifecycle=v_state, dispatch_enabled=(v_state='active'),
      pause_reason=CASE WHEN v_state='paused' THEN 'manual' ELSE NULL END
  WHERE id=p_reservation_id;
  UPDATE public.campaign_occurrences_f4e
  SET dispatch_enabled=(v_state='active')
  WHERE reservation_id=p_reservation_id AND status='planned';
  IF v_state='cancelled' THEN
    UPDATE public.campaign_network_slots_f4e SET state='cancelled',finished_at=now()
    WHERE reservation_id=p_reservation_id AND state='planned';
    UPDATE public.publish_jobs j SET status='failed',finished_at=now(),
      last_error='Campanha cancelada antes do disparo'
    FROM public.campaign_network_slots_f4e s
    WHERE s.publish_job_id=j.id AND s.reservation_id=p_reservation_id
      AND s.state='cancelled' AND j.status='pending'
      AND j.publication_origin='campaign';
    UPDATE public.campaign_reservations_f4e SET status='released',released_at=now()
    WHERE id=p_reservation_id;
  END IF;
  RETURN v_state;
END; $$;

REVOKE ALL ON FUNCTION public.activate_campaign_networks_f4e(uuid,uuid,uuid,text)
  FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.change_campaign_lifecycle_f4e(uuid,uuid,uuid,text)
  FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.activate_campaign_networks_f4e(uuid,uuid,uuid,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.change_campaign_lifecycle_f4e(uuid,uuid,uuid,text) TO service_role;
COMMIT;

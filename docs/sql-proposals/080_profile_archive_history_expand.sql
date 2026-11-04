-- PROPOSTA INERTE (NÃO EXECUTAR no Supabase compartilhado sem gate de rollout).
-- Fase EXPAND: arquivar perfil, preservar históricos e cancelar intenção de despacho.
-- Aplicar somente após testes PostgreSQL descartáveis + revisão de produção.
-- Essa DDL NÃO altera cron.job, pg_net, jobstores ou serviços.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS archived_at timestamptz;

CREATE INDEX IF NOT EXISTS profiles_active_per_account_idx
  ON public.profiles(user_id) WHERE archived_at IS NULL;

-- O trigger de compatibilidade de clientes antigos continua com teto 3; só
-- deixa de contar tombstones quando o rollout tiver sido autorizado.
CREATE OR REPLACE FUNCTION public.enforce_profile_limit()
RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_temp' AS $fn$
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext(NEW.user_id::text));
  IF current_user='service_role'
     AND current_setting('app.profile_quota_rpc',true)='on' THEN
    RETURN NEW;
  END IF;
  IF (SELECT count(*) FROM public.profiles
      WHERE user_id=NEW.user_id AND archived_at IS NULL) >= 3 THEN
    RAISE EXCEPTION 'profile_limit_exceeded' USING ERRCODE='P0001';
  END IF;
  RETURN NEW;
END; $fn$;

-- Preserva Free=1 / Pro=3 / Premium=5 / ADMIN livre.
-- Mesma trava de conta existente, agora contando apenas perfis não arquivados.
CREATE OR REPLACE FUNCTION public.insert_profile_with_plan_quota(
    p_user_id uuid, p_nome text, p_email text,
    p_telefone text DEFAULT NULL, p_endereco text DEFAULT NULL)
RETURNS SETOF public.profiles
LANGUAGE plpgsql SET search_path TO 'public', 'pg_temp' AS $fn$
DECLARE v_access text; v_tier text; v_max integer;
BEGIN
  SELECT access::text,
         CASE WHEN plan_tier='plus' THEN 'pro' ELSE plan_tier END
    INTO v_access,v_tier FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext(p_user_id::text));
  IF v_access <> 'ADMIN' THEN
    SELECT max_profiles_per_account INTO v_max
      FROM public.plan_limits WHERE tier=v_tier;
    IF v_max IS NULL THEN
      RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001';
    END IF;
    IF (SELECT count(*) FROM public.profiles
        WHERE user_id=p_user_id AND archived_at IS NULL) >= v_max THEN
      RAISE EXCEPTION 'profile_limit_exceeded' USING ERRCODE='P0001';
    END IF;
  END IF;
  PERFORM set_config('app.profile_quota_rpc','on',true);
  RETURN QUERY INSERT INTO public.profiles
    (user_id,kind,nome,email,telefone,endereco,plan_tier)
  VALUES (p_user_id,'secundario',p_nome,p_email,p_telefone,p_endereco,
          CASE WHEN v_tier='pro' THEN 'plus' ELSE v_tier END)
  RETURNING *;
END; $fn$;

-- Invocável SOMENTE pelo backend service_role, já autenticado e com ownership.
-- Transação única impede novo claim após marcar todas as agendas canceladas.
-- As chamadas externas já iniciadas não podem ser desfeitas; seus resultados
-- continuam finalizáveis/conciliáveis (succeeded,failed,unknown).
CREATE OR REPLACE FUNCTION public.archive_profile_with_history(
  p_user_id uuid, p_profile_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER
SET search_path TO '' AS $fn$
DECLARE
  v_profile record;
  v_res record;
  v_now timestamptz := now();
  v_schedules integer := 0;
  v_queued integer := 0;
  v_campaigns integer := 0;
BEGIN
  IF p_user_id IS NULL OR p_profile_id IS NULL THEN
    RAISE EXCEPTION 'profile_not_owned' USING ERRCODE='P0001';
  END IF;

  PERFORM 1 FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001';
  END IF;
  SELECT id,kind,archived_at INTO v_profile
  FROM public.profiles
  WHERE id=p_profile_id AND user_id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'profile_not_owned' USING ERRCODE='P0001';
  END IF;
  IF v_profile.kind='principal' THEN
    RAISE EXCEPTION 'principal_profile_cannot_be_archived'
      USING ERRCODE='P0001';
  END IF;
  IF v_profile.archived_at IS NOT NULL THEN
    RETURN jsonb_build_object('status','archived','already_archived',true);
  END IF;

  -- Marcação no início da MESMA transação; invisível até commit em conjunto
  -- com cancelamentos, e leitura operacional passa a rejeitar esse perfil.
  UPDATE public.profiles SET archived_at=v_now
  WHERE id=p_profile_id AND user_id=p_user_id;

  -- Não apagar schedulers: publish_jobs.scheduler_id é NOT NULL e ON DELETE
  -- CASCADE, inclusive para jobs já concluídos. Cancelar dispatch preserva FK.
  UPDATE public.schedulers
  SET dispatch_cancelled_at=COALESCE(dispatch_cancelled_at,v_now),
      dispatch_revision=dispatch_revision+1
  WHERE user_id=p_user_id AND profile_id=p_profile_id
    AND dispatch_cancelled_at IS NULL;
  GET DIAGNOSTICS v_schedules = ROW_COUNT;

  -- Usar função F4E canônica: pausa dispatch, cancela slots planejados e
  -- preserva slots running/terminais para finalização e conciliação.
  FOR v_res IN SELECT id FROM public.campaign_reservations_f4e
    WHERE user_id=p_user_id AND profile_id=p_profile_id
      AND lifecycle IN ('preparing','active','paused')
    ORDER BY id
  LOOP
    PERFORM public.change_campaign_lifecycle_f4e(
      p_user_id,p_profile_id,v_res.id,'cancel');
    v_campaigns := v_campaigns + 1;
  END LOOP;

  -- Pendências legacy nunca entregues podem sair da fila. Não apagar
  -- running/unknown/succeeded/failed: resultado histórico/conciliável.
  DELETE FROM public.publish_jobs
  WHERE user_id=p_user_id AND profile_id=p_profile_id
    AND publication_origin='legacy' AND status='pending'
    AND external_started_at IS NULL;
  GET DIAGNOSTICS v_queued = ROW_COUNT;

  RETURN jsonb_build_object(
    'status','archived',
    'schedules_cancelled',v_schedules,
    'pending_legacy_removed',v_queued,
    'campaigns_cancelled',v_campaigns);
END; $fn$;

REVOKE ALL ON FUNCTION public.archive_profile_with_history(uuid,uuid)
  FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.archive_profile_with_history(uuid,uuid)
  TO service_role;

COMMIT;

-- F4C1: cotas opt-in dos envios imediatos e horários recorrentes.
-- Supabase compartilhado: versão main anterior continua operacional, sem trigger
-- global em posts, schedulers ou publish_jobs. Registro obrigatório antes de deploy.
BEGIN;
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.plan_immediate_dispatches (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    post_id integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_plan_immediate_profile_window
    ON public.plan_immediate_dispatches(user_id, profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_plan_immediate_post
    ON public.plan_immediate_dispatches(post_id, created_at DESC);

-- Recorrências são liberadas junto com a exclusão do post; já um envio
-- imediato consumido permanece registrado por uma hora, mesmo se o post
-- for excluído. Isso impede contornar a cota publicando e apagando.
CREATE TABLE IF NOT EXISTS public.plan_recurring_slots (
    post_id integer NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    weekday smallint NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    slot_time time NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (post_id, weekday, slot_time)
);
CREATE INDEX IF NOT EXISTS idx_plan_recurring_profile_weekday
    ON public.plan_recurring_slots(user_id, profile_id, weekday);

ALTER TABLE public.plan_immediate_dispatches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plan_recurring_slots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.plan_immediate_dispatches, public.plan_recurring_slots
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, DELETE ON public.plan_immediate_dispatches, public.plan_recurring_slots
    TO service_role;

-- Reserva validada e serializada pela linha da CONTA. Cada post-raiz
-- corresponde a uma rede. Para cron, cada combinação dia+horário consome
-- uma unidade naquele dia; para Agora, uma rede consome uma unidade na
-- janela móvel de 60 minutos. Os jobs legados são considerados na leitura,
-- mas não passam por este controle opt-in até o release futuro da main.
CREATE OR REPLACE FUNCTION public.reserve_post_plan_quota(
    p_user_id uuid,
    p_profile_id uuid,
    p_post_id integer,
    p_kind text,
    p_days smallint[] DEFAULT '{}',
    p_times time[] DEFAULT '{}',
    p_reuse_existing boolean DEFAULT false
) RETURNS integer
LANGUAGE plpgsql SECURITY INVOKER SET search_path=public,pg_temp AS $$
DECLARE
    v_access text;
    v_tier text;
    v_max integer;
    v_reserved integer;
    v_legacy integer;
    v_day smallint;
BEGIN
    SELECT access::text, CASE WHEN plan_tier='plus' THEN 'pro' ELSE plan_tier END
      INTO v_access,v_tier FROM public.users WHERE id=p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.profiles
                    WHERE id=p_profile_id AND user_id=p_user_id) THEN
        RAISE EXCEPTION 'profile_not_owned' USING ERRCODE='P0001';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.posts
                    WHERE id=p_post_id AND post_id IS NULL
                      AND user_id=p_user_id AND profile_id=p_profile_id) THEN
        RAISE EXCEPTION 'post_not_owned' USING ERRCODE='P0001';
    END IF;
    IF p_kind NOT IN ('immediate','recurring') OR p_kind IS NULL THEN
        RAISE EXCEPTION 'invalid_quota_kind' USING ERRCODE='P0001';
    END IF;
    IF p_kind='recurring' AND (
        cardinality(p_days) NOT BETWEEN 1 AND 7
        OR cardinality(p_times) NOT BETWEEN 1 AND 5
        OR p_days IS NULL OR p_times IS NULL
        OR EXISTS(SELECT 1 FROM unnest(p_days) AS d(day)
                  WHERE day IS NULL OR day NOT BETWEEN 0 AND 6)
        OR EXISTS(SELECT 1 FROM unnest(p_times) AS t(slot_time) WHERE slot_time IS NULL)
        OR (SELECT count(*) FROM unnest(p_days) AS d(day)) <>
           (SELECT count(DISTINCT day) FROM unnest(p_days) AS d(day))
        OR (SELECT count(*) FROM unnest(p_times) AS t(slot_time)) <>
           (SELECT count(DISTINCT slot_time) FROM unnest(p_times) AS t(slot_time))
    ) THEN
        RAISE EXCEPTION 'invalid_recurring_slots' USING ERRCODE='P0001';
    END IF;

    -- ADMIN não tem cotas comerciais; validações de identidade e formato
    -- continuam obrigatórias, mas não é necessário registrar reserva.
    IF v_access='ADMIN' THEN RETURN 0; END IF;

    IF p_kind='immediate' THEN
        -- Limpeza oportunista: retém até 24 h para diagnóstico sem crescer
        -- indefinidamente em perfis ativos; a cota lê apenas a última hora.
        DELETE FROM public.plan_immediate_dispatches
        WHERE user_id=p_user_id AND profile_id=p_profile_id
          AND created_at<now()-interval '24 hours';
        -- A reserva criada no lote não deve ser cobrada de novo quando o
        -- frontend chamar /posts/{id}/publish para o mesmo post.
        IF p_reuse_existing AND EXISTS(
            SELECT 1 FROM public.plan_immediate_dispatches
            WHERE user_id=p_user_id AND profile_id=p_profile_id
              AND post_id=p_post_id AND created_at>now()-interval '1 hour'
        ) THEN RETURN 0; END IF;
        SELECT immediate_per_hour INTO v_max
        FROM public.plan_limits WHERE tier=v_tier;
        IF v_max IS NULL THEN
            RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001';
        END IF;
        SELECT count(*) INTO v_reserved
        FROM public.plan_immediate_dispatches
        WHERE user_id=p_user_id AND profile_id=p_profile_id
          AND created_at>now()-interval '1 hour';

        -- Incluir as ocorrências recentes dos posts "Agora" legados que
        -- não tiveram reserva nova; não contar partes da thread nem duplicar
        -- o mesmo post já registrado nesta tabela.
        SELECT count(DISTINCT j.post_id) INTO v_legacy
        FROM public.publish_jobs j
        JOIN public.posts p ON p.id=j.post_id AND p.post_id IS NULL
        WHERE j.user_id=p_user_id AND j.profile_id=p_profile_id
          AND p.publish_immediately=true
          AND j.created_at>now()-interval '1 hour'
          AND NOT EXISTS (
              SELECT 1 FROM public.plan_immediate_dispatches q
              WHERE q.post_id=j.post_id AND q.user_id=p_user_id
                AND q.profile_id=p_profile_id
                AND q.created_at>now()-interval '1 hour'
          );
        IF v_reserved+v_legacy >= v_max THEN
            RAISE EXCEPTION 'plan_immediate_quota_exceeded' USING ERRCODE='P0001';
        END IF;
        INSERT INTO public.plan_immediate_dispatches(user_id,profile_id,post_id)
        VALUES (p_user_id,p_profile_id,p_post_id);
        RETURN v_max-v_reserved-v_legacy-1;
    END IF;

    SELECT recurring_slots_per_day INTO v_max
    FROM public.plan_limits WHERE tier=v_tier;
    IF v_max IS NULL THEN
        RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001';
    END IF;
    FOREACH v_day IN ARRAY p_days LOOP
        SELECT count(*) INTO v_reserved
        FROM public.plan_recurring_slots
        WHERE user_id=p_user_id AND profile_id=p_profile_id
          AND weekday=v_day;

        -- Cron da main/legado é contado apenas quando não há reserva
        -- equivalente, evitando dupla contagem do próprio post F4C1.
        SELECT count(*) INTO v_legacy
        FROM public.schedulers s
        CROSS JOIN LATERAL unnest(
            coalesce(s.days_of_week, ARRAY[s.day_of_week]::smallint[])
        ) AS wd(day)
        WHERE s.user_id=p_user_id AND s.profile_id=p_profile_id
          AND s.trigger='cron' AND wd.day=v_day
          AND NOT EXISTS (
              SELECT 1 FROM public.plan_recurring_slots r
              WHERE r.post_id=s.post_id AND r.weekday=wd.day
                AND r.slot_time=s.time
          );
        IF v_reserved+v_legacy+cardinality(p_times)>v_max THEN
            RAISE EXCEPTION 'plan_recurring_quota_exceeded' USING ERRCODE='P0001';
        END IF;
    END LOOP;
    INSERT INTO public.plan_recurring_slots
        (post_id,user_id,profile_id,weekday,slot_time)
    SELECT p_post_id,p_user_id,p_profile_id,d.weekday,t.slot_time
    FROM unnest(p_days) AS d(weekday)
    CROSS JOIN unnest(p_times) AS t(slot_time);
    RETURN v_max;
END; $$;

-- Compensação apenas de criação que falhou antes de existir scheduler
-- ou publish_job. Nunca liberar após timeout/erro de chamada externa.
CREATE OR REPLACE FUNCTION public.release_failed_post_plan_quota(
    p_user_id uuid, p_profile_id uuid, p_post_id integer
) RETURNS integer
LANGUAGE plpgsql SECURITY INVOKER SET search_path=public,pg_temp AS $$
DECLARE v_removed integer;
BEGIN
    PERFORM 1 FROM public.users WHERE id=p_user_id FOR UPDATE;
    IF NOT FOUND THEN RETURN 0; END IF;
    IF EXISTS(SELECT 1 FROM public.schedulers WHERE post_id=p_post_id)
       OR EXISTS(SELECT 1 FROM public.publish_jobs WHERE post_id=p_post_id) THEN
        RETURN 0;
    END IF;
    DELETE FROM public.plan_immediate_dispatches
    WHERE user_id=p_user_id AND profile_id=p_profile_id AND post_id=p_post_id;
    GET DIAGNOSTICS v_removed = ROW_COUNT;
    RETURN v_removed;
END; $$;

REVOKE ALL ON FUNCTION public.reserve_post_plan_quota(
    uuid,uuid,integer,text,smallint[],time[],boolean)
    FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.release_failed_post_plan_quota(
    uuid,uuid,integer)
    FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.reserve_post_plan_quota(
    uuid,uuid,integer,text,smallint[],time[],boolean) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_failed_post_plan_quota(
    uuid,uuid,integer) TO service_role;

COMMIT;

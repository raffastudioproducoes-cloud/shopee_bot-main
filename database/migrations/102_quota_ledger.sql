-- Fase 1, item 1: livro de consumo de cota (quota_ledger). Apagar post NÃO devolve cota.
-- Decisão do Rafa: "quem manda é o banco; o cliente não pode subtrair o que já usou".
--
-- ADITIVA e IDEMPOTENTE. Banco compartilhado com a main 3.20.1: as duas funções
-- de 073 mantêm assinatura e tipo de retorno; a main continua chamando igual e
-- passa a ser medida pelo livro. Nenhuma tabela existente é alterada.
--
-- Semântica:
--  * immediate: consumo = SUM(amount) do livro na janela móvel de 60 min por perfil.
--    Data de corte = quota_ledger_cutover.cutover_at (momento em que esta migração
--    foi aplicada). Reservas em plan_immediate_dispatches ANTERIORES ao corte
--    continuam contando (fallback); posteriores contam só pelo livro (sem dupla contagem).
--  * recurring: capacidade = horários vivos em plan_recurring_slots (como em 073)
--    + horários APAGADOS nas últimas 24 h (linha 'recurring_released', gravada por
--    trigger quando a FK CASCADE de posts apaga o horário). 24 h após a exclusão o
--    dia da semana daquele horário já terminou em qualquer fuso, então "publicar,
--    apagar e recriar no mesmo dia" deixa de passar do limite.
--  * Só release_failed_post_plan_quota (criação que falhou ANTES de existir
--    scheduler/publish_job, nos últimos 15 min) pode compensar, com linha negativa.
--
-- Imutável: UPDATE/DELETE/TRUNCATE bloqueados para TODOS os papéis. Sem FK para
-- users/profiles/posts, então apagar conta/perfil/post não é bloqueado nem apaga o
-- livro. Expurgo (ex.: retenção LGPD de conta apagada) exige migração controlada
-- que desabilite o trigger explicitamente.
--
-- Reversão (manual, revisada):
--   BEGIN;
--   -- reaplicar o corpo das duas funções de 073_post_publication_plan_quotas.sql
--   DROP TRIGGER IF EXISTS trg_plan_recurring_slots_ledger_release ON public.plan_recurring_slots;
--   DROP FUNCTION IF EXISTS public.quota_ledger_on_slot_release();
--   DROP FUNCTION IF EXISTS public.record_quota_use(uuid,uuid,text,text,integer,uuid,integer,text,smallint,time);
--   DROP TABLE IF EXISTS public.quota_ledger_cutover;
--   DROP TABLE IF EXISTS public.quota_ledger;  -- perde o histórico de consumo
--   DROP FUNCTION IF EXISTS public.quota_ledger_block_mutation();
--   COMMIT;
BEGIN;
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.quota_ledger (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id uuid NOT NULL,
    profile_id uuid,
    kind text NOT NULL CHECK (kind IN ('immediate','recurring','recurring_released')),
    network text,
    post_id integer,
    scheduler_id uuid,
    weekday smallint CHECK (weekday BETWEEN 0 AND 6),
    slot_time time,
    amount integer NOT NULL DEFAULT 1 CHECK (amount <> 0),
    ref text CHECK (ref IS NULL OR char_length(ref) <= 200),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_quota_ledger_user_kind_created
    ON public.quota_ledger (user_id, kind, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quota_ledger_profile_kind_created
    ON public.quota_ledger (profile_id, kind, created_at DESC);

CREATE TABLE IF NOT EXISTS public.quota_ledger_cutover (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),
    cutover_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.quota_ledger_cutover (id) VALUES (true) ON CONFLICT (id) DO NOTHING;

ALTER TABLE public.quota_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quota_ledger_cutover ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.quota_ledger, public.quota_ledger_cutover
    FROM PUBLIC, anon, authenticated, service_role;
-- service_role só LÊ; toda escrita passa por funções SECURITY DEFINER abaixo.
GRANT SELECT ON TABLE public.quota_ledger, public.quota_ledger_cutover TO service_role;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='quota_ledger'
                 AND policyname='block_all_api') THEN
    CREATE POLICY block_all_api ON public.quota_ledger FOR ALL USING (false) WITH CHECK (false);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='quota_ledger_cutover'
                 AND policyname='block_all_api') THEN
    CREATE POLICY block_all_api ON public.quota_ledger_cutover FOR ALL USING (false) WITH CHECK (false);
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.quota_ledger_block_mutation()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    RAISE EXCEPTION 'quota_ledger_immutable' USING ERRCODE = 'P0001';
END; $$;
REVOKE ALL ON FUNCTION public.quota_ledger_block_mutation() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS trg_quota_ledger_immutable ON public.quota_ledger;
CREATE TRIGGER trg_quota_ledger_immutable
    BEFORE UPDATE OR DELETE ON public.quota_ledger
    FOR EACH ROW EXECUTE FUNCTION public.quota_ledger_block_mutation();
DROP TRIGGER IF EXISTS trg_quota_ledger_no_truncate ON public.quota_ledger;
CREATE TRIGGER trg_quota_ledger_no_truncate
    BEFORE TRUNCATE ON public.quota_ledger
    FOR EACH STATEMENT EXECUTE FUNCTION public.quota_ledger_block_mutation();
DROP TRIGGER IF EXISTS trg_quota_ledger_cutover_immutable ON public.quota_ledger_cutover;
CREATE TRIGGER trg_quota_ledger_cutover_immutable
    BEFORE UPDATE OR DELETE ON public.quota_ledger_cutover
    FOR EACH ROW EXECUTE FUNCTION public.quota_ledger_block_mutation();

-- Único ponto de escrita exposto: só CONSUMO (amount > 0). Compensação negativa
-- existe apenas dentro de release_failed_post_plan_quota.
CREATE OR REPLACE FUNCTION public.record_quota_use(
    p_user_id uuid,
    p_profile_id uuid,
    p_kind text,
    p_network text DEFAULT NULL,
    p_post_id integer DEFAULT NULL,
    p_scheduler_id uuid DEFAULT NULL,
    p_amount integer DEFAULT 1,
    p_ref text DEFAULT NULL,
    p_weekday smallint DEFAULT NULL,
    p_slot_time time DEFAULT NULL
) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_id bigint;
BEGIN
    IF p_user_id IS NULL OR p_kind IS NULL OR p_kind NOT IN ('immediate','recurring') THEN
        RAISE EXCEPTION 'invalid_quota_use' USING ERRCODE = 'P0001';
    END IF;
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'invalid_quota_amount' USING ERRCODE = 'P0001';
    END IF;
    INSERT INTO public.quota_ledger
        (user_id, profile_id, kind, network, post_id, scheduler_id, amount, ref, weekday, slot_time)
    VALUES
        (p_user_id, p_profile_id, p_kind, p_network, p_post_id, p_scheduler_id, p_amount,
         p_ref, p_weekday, p_slot_time)
    RETURNING id INTO v_id;
    RETURN v_id;
END; $$;
REVOKE ALL ON FUNCTION public.record_quota_use(uuid,uuid,text,text,integer,uuid,integer,text,smallint,time)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_quota_use(uuid,uuid,text,text,integer,uuid,integer,text,smallint,time)
    TO service_role;

-- Horário recorrente apagado (CASCADE de posts) continua ocupando a vaga do dia
-- por 24 h. Apagar perfil/conta não grava (o perfil já não existe). A compensação
-- de criação falha marca a transação com app.quota_compensation='on'.
CREATE OR REPLACE FUNCTION public.quota_ledger_on_slot_release()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF coalesce(current_setting('app.quota_compensation', true), '') = 'on' THEN
        RETURN OLD;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.profiles WHERE id = OLD.profile_id) THEN
        RETURN OLD;
    END IF;
    -- Mesma serialização da reserva: a linha da conta.
    PERFORM 1 FROM public.users WHERE id = OLD.user_id FOR UPDATE;
    IF NOT FOUND THEN RETURN OLD; END IF;
    INSERT INTO public.quota_ledger
        (user_id, profile_id, kind, post_id, weekday, slot_time, amount, ref)
    VALUES
        (OLD.user_id, OLD.profile_id, 'recurring_released', OLD.post_id, OLD.weekday,
         OLD.slot_time, 1, 'plan_recurring_slots:delete');
    RETURN OLD;
END; $$;
REVOKE ALL ON FUNCTION public.quota_ledger_on_slot_release() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS trg_plan_recurring_slots_ledger_release ON public.plan_recurring_slots;
CREATE TRIGGER trg_plan_recurring_slots_ledger_release
    AFTER DELETE ON public.plan_recurring_slots
    FOR EACH ROW EXECUTE FUNCTION public.quota_ledger_on_slot_release();

-- Mesma assinatura e retorno de 073 (compatível com a main 3.20.1).
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
    v_network text;
    v_cutover timestamptz;
    v_max integer;
    v_reserved integer;
    v_released integer;
    v_legacy integer;
    v_day smallint;
    v_time time;
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
    SELECT network INTO v_network FROM public.posts
     WHERE id=p_post_id AND post_id IS NULL
       AND user_id=p_user_id AND profile_id=p_profile_id;
    IF NOT FOUND THEN
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

    -- ADMIN não tem cotas comerciais (isento, como em 073): nada é registrado.
    IF v_access='ADMIN' THEN RETURN 0; END IF;

    IF p_kind='immediate' THEN
        SELECT cutover_at INTO v_cutover FROM public.quota_ledger_cutover WHERE id;
        v_cutover := coalesce(v_cutover, now());
        DELETE FROM public.plan_immediate_dispatches
        WHERE user_id=p_user_id AND profile_id=p_profile_id
          AND created_at<now()-interval '24 hours';
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
        -- Fonte do consumo: o livro (imune a apagar post ou reserva).
        SELECT coalesce(sum(amount),0) INTO v_reserved
        FROM public.quota_ledger
        WHERE user_id=p_user_id AND profile_id=p_profile_id AND kind='immediate'
          AND created_at>now()-interval '1 hour';
        -- Fallback: reservas de antes do corte, que não têm linha no livro.
        v_reserved := v_reserved + (
            SELECT count(*) FROM public.plan_immediate_dispatches
            WHERE user_id=p_user_id AND profile_id=p_profile_id
              AND created_at>now()-interval '1 hour' AND created_at<v_cutover);
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
          )
          AND NOT EXISTS (
              SELECT 1 FROM public.quota_ledger l
              WHERE l.post_id=j.post_id AND l.user_id=p_user_id
                AND l.kind='immediate' AND l.created_at>now()-interval '1 hour'
          );
        IF v_reserved+v_legacy >= v_max THEN
            RAISE EXCEPTION 'plan_immediate_quota_exceeded' USING ERRCODE='P0001';
        END IF;
        INSERT INTO public.plan_immediate_dispatches(user_id,profile_id,post_id)
        VALUES (p_user_id,p_profile_id,p_post_id);
        PERFORM public.record_quota_use(p_user_id, p_profile_id, 'immediate', v_network,
                                        p_post_id, NULL, 1, 'reserve_post_plan_quota');
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

        -- Horários apagados nas últimas 24 h continuam ocupando o dia.
        SELECT coalesce(sum(amount),0) INTO v_released
        FROM public.quota_ledger
        WHERE user_id=p_user_id AND profile_id=p_profile_id
          AND kind='recurring_released' AND weekday=v_day
          AND created_at>now()-interval '24 hours';

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
        IF v_reserved+v_released+v_legacy+cardinality(p_times)>v_max THEN
            RAISE EXCEPTION 'plan_recurring_quota_exceeded' USING ERRCODE='P0001';
        END IF;
    END LOOP;
    INSERT INTO public.plan_recurring_slots
        (post_id,user_id,profile_id,weekday,slot_time)
    SELECT p_post_id,p_user_id,p_profile_id,d.weekday,t.slot_time
    FROM unnest(p_days) AS d(weekday)
    CROSS JOIN unnest(p_times) AS t(slot_time);
    FOREACH v_day IN ARRAY p_days LOOP
        FOREACH v_time IN ARRAY p_times LOOP
            PERFORM public.record_quota_use(p_user_id, p_profile_id, 'recurring', v_network,
                                            p_post_id, NULL, 1, 'reserve_post_plan_quota',
                                            v_day, v_time);
        END LOOP;
    END LOOP;
    RETURN v_max;
END; $$;

-- Mesma assinatura e retorno de 073. Agora SECURITY DEFINER: é o único lugar que
-- grava compensação negativa. Só compensa a própria conta/perfil, post sem
-- scheduler nem publish_job, e reservas dos últimos 15 minutos (criação falha).
CREATE OR REPLACE FUNCTION public.release_failed_post_plan_quota(
    p_user_id uuid, p_profile_id uuid, p_post_id integer
) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_immediate integer;
    v_recurring integer;
BEGIN
    PERFORM 1 FROM public.users WHERE id=p_user_id FOR UPDATE;
    IF NOT FOUND THEN RETURN 0; END IF;
    -- Não exige o post existir: a main 3.20.1 chama depois de apagar o post.
    -- Para recorrência, chamar ANTES de apagar (senão o CASCADE já gravou a vaga).
    IF EXISTS(SELECT 1 FROM public.schedulers WHERE post_id=p_post_id)
       OR EXISTS(SELECT 1 FROM public.publish_jobs WHERE post_id=p_post_id) THEN
        RETURN 0;
    END IF;
    DELETE FROM public.plan_immediate_dispatches
    WHERE user_id=p_user_id AND profile_id=p_profile_id AND post_id=p_post_id
      AND created_at>now()-interval '15 minutes';
    GET DIAGNOSTICS v_immediate = ROW_COUNT;

    PERFORM set_config('app.quota_compensation', 'on', true);
    DELETE FROM public.plan_recurring_slots
    WHERE user_id=p_user_id AND profile_id=p_profile_id AND post_id=p_post_id
      AND created_at>now()-interval '15 minutes';
    GET DIAGNOSTICS v_recurring = ROW_COUNT;
    PERFORM set_config('app.quota_compensation', 'off', true);

    -- Compensa só o que o livro registrou para este post (nunca mais que isso).
    v_immediate := least(v_immediate, (
        SELECT coalesce(sum(amount),0) FROM public.quota_ledger
        WHERE user_id=p_user_id AND post_id=p_post_id AND kind='immediate'));
    v_recurring := least(v_recurring, (
        SELECT coalesce(sum(amount),0) FROM public.quota_ledger
        WHERE user_id=p_user_id AND post_id=p_post_id AND kind='recurring'));
    IF v_immediate > 0 THEN
        INSERT INTO public.quota_ledger (user_id, profile_id, kind, post_id, amount, ref)
        VALUES (p_user_id, p_profile_id, 'immediate', p_post_id, -v_immediate,
                'release_failed_post_plan_quota');
    END IF;
    IF v_recurring > 0 THEN
        INSERT INTO public.quota_ledger (user_id, profile_id, kind, post_id, amount, ref)
        VALUES (p_user_id, p_profile_id, 'recurring', p_post_id, -v_recurring,
                'release_failed_post_plan_quota');
    END IF;
    RETURN v_immediate + v_recurring;
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

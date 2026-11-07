-- Cota manual por conta (não por perfil ou plano), dia civil de Brasília.
-- Migração aditiva, retrocompatível com staging/main; não altera scheduler/pg_cron.
CREATE TABLE IF NOT EXISTS public.analytics_manual_refresh_quota (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    quota_day DATE NOT NULL,
    used SMALLINT NOT NULL DEFAULT 0 CHECK (used BETWEEN 0 AND 10),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.analytics_manual_refresh_quota ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.analytics_manual_refresh_quota FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.analytics_manual_refresh_quota TO service_role;

CREATE OR REPLACE FUNCTION public.analytics_manual_refresh_status(p_user_id UUID)
RETURNS JSONB LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_access TEXT;
    v_day DATE := (now() AT TIME ZONE 'America/Sao_Paulo')::date;
    v_used INT := 0;
    v_reset TIMESTAMPTZ := ((v_day + 1)::timestamp AT TIME ZONE 'America/Sao_Paulo');
BEGIN
    SELECT access INTO v_access FROM public.users WHERE id = p_user_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Conta não encontrada'; END IF;
    IF v_access = 'ADMIN' THEN
        RETURN jsonb_build_object('unlimited', true, 'used', 0, 'remaining', null,
                                  'limit', null, 'reset_at', v_reset);
    END IF;
    SELECT used INTO v_used FROM public.analytics_manual_refresh_quota
     WHERE user_id = p_user_id AND quota_day = v_day;
    v_used := COALESCE(v_used, 0);
    RETURN jsonb_build_object('unlimited', false, 'used', v_used,
                              'remaining', 10 - v_used, 'limit', 10, 'reset_at', v_reset);
END;
$$;
REVOKE ALL ON FUNCTION public.analytics_manual_refresh_status(UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.analytics_manual_refresh_status(UUID) TO service_role;

-- A mesma transação reserva quota E claims; tentativas no cooldown não gastam cota.
-- Limite de até 12 perfis por clique protege as APIs externas da execução em lote.
CREATE OR REPLACE FUNCTION public.claim_analytics_manual_refresh(p_user_id UUID, p_profile_ids UUID[])
RETURNS JSONB LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_access TEXT;
    v_day DATE := (now() AT TIME ZONE 'America/Sao_Paulo')::date;
    v_used INT := 0;
    v_id UUID;
    v_token UUID;
    v_claims JSONB := '{}'::jsonb;
BEGIN
    SELECT access INTO v_access FROM public.users WHERE id = p_user_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Conta não encontrada'; END IF;
    IF p_profile_ids IS NULL OR cardinality(p_profile_ids) < 1 OR cardinality(p_profile_ids) > 12
       OR EXISTS (SELECT 1 FROM unnest(p_profile_ids) AS requested(profile_id)
                   WHERE requested.profile_id IS NULL OR NOT EXISTS (
                       SELECT 1 FROM public.profiles AS p
                        WHERE p.id = requested.profile_id AND p.user_id = p_user_id)) THEN
        RAISE EXCEPTION 'Perfis inválidos ou não pertencentes à conta';
    END IF;

    IF v_access IS DISTINCT FROM 'ADMIN' THEN
        INSERT INTO public.analytics_manual_refresh_quota(user_id, quota_day, used)
        VALUES(p_user_id, v_day, 0)
        ON CONFLICT(user_id) DO UPDATE
            SET quota_day = EXCLUDED.quota_day, used = 0, updated_at = now()
          WHERE public.analytics_manual_refresh_quota.quota_day <> EXCLUDED.quota_day;
        SELECT used INTO v_used FROM public.analytics_manual_refresh_quota
         WHERE user_id = p_user_id FOR UPDATE;
        IF v_used >= 10 THEN
            RETURN jsonb_build_object('state', 'limit_reached',
                                      'quota', public.analytics_manual_refresh_status(p_user_id));
        END IF;
    END IF;

    FOR v_id IN SELECT DISTINCT unnest(p_profile_ids) LOOP
        IF v_access = 'ADMIN' THEN
            -- ADMIN não tem cota nem cooldown diário; só impede coleta concorrente.
            INSERT INTO public.analytics_daily_refreshes(user_id, profile_id)
            VALUES(p_user_id, v_id) ON CONFLICT(user_id, profile_id) DO NOTHING;
            UPDATE public.analytics_daily_refreshes
               SET claim_token = gen_random_uuid(), locked_until = now() + interval '60 seconds',
                   last_attempt_at = now()
             WHERE user_id = p_user_id AND profile_id = v_id
               AND (locked_until IS NULL OR locked_until < now())
            RETURNING claim_token INTO v_token;
        ELSE
            v_token := public.claim_analytics_refresh(p_user_id, v_id, 300);
        END IF;
        IF v_token IS NOT NULL THEN
            v_claims := v_claims || jsonb_build_object(v_id::text, v_token::text);
        END IF;
    END LOOP;
    IF v_claims = '{}'::jsonb THEN
        RETURN jsonb_build_object('state', 'recent',
                                  'quota', public.analytics_manual_refresh_status(p_user_id));
    END IF;
    IF v_access IS DISTINCT FROM 'ADMIN' THEN
        UPDATE public.analytics_manual_refresh_quota
           SET used = used + 1, updated_at = now() WHERE user_id = p_user_id;
    END IF;
    RETURN jsonb_build_object('state', 'accepted', 'claims', v_claims,
                              'quota', public.analytics_manual_refresh_status(p_user_id));
END;
$$;
REVOKE ALL ON FUNCTION public.claim_analytics_manual_refresh(UUID, UUID[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_analytics_manual_refresh(UUID, UUID[]) TO service_role;

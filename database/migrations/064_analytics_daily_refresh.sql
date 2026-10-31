-- Cache de insights por conta/perfil, compartilhado entre staging e main.
-- Sem tokens, IDs externos, texto de posts ou dados pessoais em métricas.
CREATE TABLE IF NOT EXISTS public.analytics_daily_refreshes (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    last_attempt_at TIMESTAMPTZ,
    last_completed_at TIMESTAMPTZ,
    claim_token UUID,
    locked_until TIMESTAMPTZ,
    provider_states JSONB NOT NULL DEFAULT '{}'::jsonb,
    facebook_daily_values JSONB NOT NULL DEFAULT '[]'::jsonb,
    threads_views BIGINT CHECK (threads_views IS NULL OR threads_views >= 0),
    metrics_collected_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, profile_id)
);
CREATE INDEX IF NOT EXISTS idx_analytics_refresh_due
    ON public.analytics_daily_refreshes (last_attempt_at NULLS FIRST);
ALTER TABLE public.analytics_daily_refreshes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.analytics_daily_refreshes FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.analytics_daily_refreshes TO service_role;

-- Resgate atômico entre os dois serviços Render; o lock expira após interrupção.
-- Função INVOKER (sem bypass de RLS) executável somente pela chave de serviço.
CREATE OR REPLACE FUNCTION public.claim_analytics_refresh(
    p_user_id UUID, p_profile_id UUID, p_min_seconds INTEGER DEFAULT 86400
) RETURNS UUID
LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
DECLARE v_token UUID := gen_random_uuid();
DECLARE v_now TIMESTAMPTZ := now();
DECLARE v_claimed UUID;
BEGIN
    IF p_min_seconds < 300 OR p_min_seconds > 86400
       OR NOT EXISTS (SELECT 1 FROM public.profiles
                      WHERE id = p_profile_id AND user_id = p_user_id) THEN
        RETURN NULL;
    END IF;
    INSERT INTO public.analytics_daily_refreshes (user_id, profile_id)
    VALUES (p_user_id, p_profile_id)
    ON CONFLICT (user_id, profile_id) DO NOTHING;

    UPDATE public.analytics_daily_refreshes
       SET claim_token = v_token,
           locked_until = v_now + interval '60 seconds',
           last_attempt_at = v_now
     WHERE user_id = p_user_id AND profile_id = p_profile_id
       AND (locked_until IS NULL OR locked_until < v_now)
       AND (last_attempt_at IS NULL
            OR last_attempt_at <= v_now - make_interval(secs => p_min_seconds))
    RETURNING claim_token INTO v_claimed;
    RETURN v_claimed;
END;
$$;
REVOKE ALL ON FUNCTION public.claim_analytics_refresh(UUID, UUID, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_analytics_refresh(UUID, UUID, INTEGER) TO service_role;

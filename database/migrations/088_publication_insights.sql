-- Métricas exclusivamente de publicações identificadas pelo Auto Orbital.
-- Cache de contadores lifetime por publish_job confirmado, nunca da conta/página.
-- Aditivo e compatível com main; nenhum cron, trigger ou job adicional.
CREATE TABLE IF NOT EXISTS public.publication_insights (
    publish_job_id UUID PRIMARY KEY REFERENCES public.publish_jobs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    profile_id UUID,
    network TEXT NOT NULL CHECK (network IN ('threads', 'facebook', 'instagram', 'tiktok', 'x')),
    external_id TEXT NOT NULL,
    views BIGINT CHECK (views IS NULL OR views >= 0),
    likes BIGINT CHECK (likes IS NULL OR likes >= 0),
    comments BIGINT CHECK (comments IS NULL OR comments >= 0),
    reposts BIGINT CHECK (reposts IS NULL OR reposts >= 0),
    shares BIGINT CHECK (shares IS NULL OR shares >= 0),
    quotes BIGINT CHECK (quotes IS NULL OR quotes >= 0),
    clicks BIGINT CHECK (clicks IS NULL OR clicks >= 0),
    state TEXT NOT NULL DEFAULT 'not_collected',
    last_attempt_at TIMESTAMPTZ,
    last_completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_publication_insights_owner
    ON public.publication_insights (user_id, profile_id, network);
ALTER TABLE public.publication_insights ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.publication_insights FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.publication_insights TO service_role;
COMMENT ON TABLE public.publication_insights IS
    'Métricas lifetime por publicação confirmada e ID externo do publish_jobs; sem métricas gerais de conta.';

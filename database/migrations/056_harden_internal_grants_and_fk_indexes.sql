-- Corrige privilegios SQL que RLS, isoladamente, nao cobre.
-- A API e o scheduler usam credenciais de servidor; nao conceder acesso
-- direto a usuarios anon/authenticated sobre filas e leases internos.
-- Idempotente: aplicado manualmente no projeto autovendas em 31/10/2026.
-- Execucao pelo migrator em transacao com advisory lock.
SET LOCAL lock_timeout = '10s';

REVOKE ALL PRIVILEGES ON TABLE
    public.publication_claims,
    public.publish_jobs
FROM anon, authenticated;

-- Cobertura das seis FKs apontadas pelo Supabase Performance Advisor.
-- Nomes exclusivos; IF NOT EXISTS evita reconstruir indices ja aplicados.
CREATE INDEX IF NOT EXISTS idx_publish_jobs_post_id
    ON public.publish_jobs (post_id);

CREATE INDEX IF NOT EXISTS idx_publish_jobs_profile_id
    ON public.publish_jobs (profile_id);

CREATE INDEX IF NOT EXISTS idx_publish_jobs_scheduler_id
    ON public.publish_jobs (scheduler_id);

CREATE INDEX IF NOT EXISTS idx_publish_jobs_user_id
    ON public.publish_jobs (user_id);

CREATE INDEX IF NOT EXISTS idx_revoked_sessions_user_id
    ON public.revoked_sessions (user_id);

CREATE INDEX IF NOT EXISTS idx_temporary_media_uploads_profile_id
    ON public.temporary_media_uploads (profile_id);

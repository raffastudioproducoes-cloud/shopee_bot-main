-- Índices de desempenho para a listagem de posts e para chaves estrangeiras sem índice (linter do Supabase).
-- Aditivo: só `CREATE INDEX IF NOT EXISTS`; nenhuma coluna, dado, política ou permissão muda.
-- Tabelas pequenas hoje (<1 mil linhas); os índices preparam o crescimento por conta/perfil.
BEGIN;
SET LOCAL lock_timeout = '10s';

-- Listagem de posts: cabeças da thread por dono/perfil, mais novas primeiro (paginação por cursor).
CREATE INDEX IF NOT EXISTS idx_posts_owner_heads_created
    ON public.posts (user_id, profile_id, created_at DESC) WHERE post_id IS NULL;

-- Última execução da fila por post, e última publicação confirmada.
CREATE INDEX IF NOT EXISTS idx_publish_jobs_post_latest
    ON public.publish_jobs (post_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_publish_jobs_post_succeeded
    ON public.publish_jobs (post_id, finished_at DESC) WHERE status = 'succeeded';

-- Eventos de publicação (publicado/falhou) por post: o id do post fica dentro do JSON `metadata`.
CREATE INDEX IF NOT EXISTS idx_activities_publish_by_post
    ON public.activities ((metadata->>'post_id'), activity_id, created_at DESC) WHERE activity_id IN (1, 2);

-- Chaves estrangeiras sem índice de cobertura (apagar/atualizar perfil, usuário ou revisão varria a tabela inteira).
CREATE INDEX IF NOT EXISTS idx_campaign_draft_media_profile_id ON public.campaign_draft_media (profile_id);
CREATE INDEX IF NOT EXISTS idx_campaign_drafts_profile_id ON public.campaign_drafts (profile_id);
CREATE INDEX IF NOT EXISTS idx_plan_immediate_dispatches_profile_id ON public.plan_immediate_dispatches (profile_id);
CREATE INDEX IF NOT EXISTS idx_plan_recurring_slots_profile_id ON public.plan_recurring_slots (profile_id);
CREATE INDEX IF NOT EXISTS idx_platform_ai_settings_active_provider ON public.platform_ai_settings (environment, active_provider);
CREATE INDEX IF NOT EXISTS idx_publish_jobs_content_revision_id ON public.publish_jobs (content_revision_id) WHERE content_revision_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shopee_video_authorizations_profile_id ON public.shopee_video_authorizations (profile_id);
CREATE INDEX IF NOT EXISTS idx_shopee_video_authorizations_user_id ON public.shopee_video_authorizations (user_id);

COMMIT;

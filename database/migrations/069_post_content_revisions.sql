-- F1/R12: armazenamento inerte de revisões futuras, sem reescrever posts,
-- medias, agendas APScheduler existentes ou resultados de publicação.
-- O esquema é compartilhado entre staging e produção.
CREATE TABLE IF NOT EXISTS public.post_content_revisions (
    id bigserial PRIMARY KEY,
    post_id integer NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id uuid NOT NULL,
    profile_id uuid NOT NULL,
    snapshot jsonb NOT NULL,
    effective_after timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT post_content_revisions_snapshot_check
      CHECK (
        jsonb_typeof(snapshot) = 'object'
        AND jsonb_typeof(snapshot->'texts') = 'array'
        AND jsonb_array_length(snapshot->'texts') > 0
        AND jsonb_typeof(snapshot->'medias') = 'array'
        AND jsonb_typeof(snapshot->'product_ids') = 'array'
      )
);
CREATE INDEX IF NOT EXISTS idx_post_content_revisions_lookup
    ON public.post_content_revisions
    (post_id, user_id, profile_id, effective_after DESC, id DESC);
ALTER TABLE public.post_content_revisions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.post_content_revisions FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.post_content_revisions_id_seq FROM anon, authenticated;

-- Todos os campos novos são NULL por padrão: jobs antigos continuam idênticos.
ALTER TABLE public.publish_jobs
    ADD COLUMN IF NOT EXISTS scheduled_for timestamptz,
    ADD COLUMN IF NOT EXISTS content_revision_id bigint
      REFERENCES public.post_content_revisions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS content_snapshot jsonb;
-- Nenhuma alteração nos triggers de mídia, nos antigos cron, nos jobs ou em RLS.

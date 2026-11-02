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

-- O endpoint invoca esta função com service_role. A trava do post serializa
-- edições concorrentes e o banco define o corte; não há UPDATE no post-base.
CREATE OR REPLACE FUNCTION public.create_future_post_revision(
    p_post_id integer,
    p_user_id uuid,
    p_profile_id uuid,
    p_snapshot jsonb
)
RETURNS TABLE (revision_id bigint, cutover_at timestamptz)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_time timestamptz;
    v_revision_id bigint;
BEGIN
    PERFORM 1 FROM public.posts p
    WHERE p.id = p_post_id
      AND p.user_id = p_user_id
      AND p.profile_id = p_profile_id
      AND p.post_id IS NULL
      AND p.publish_immediately = false
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'POST_NOT_EDITABLE' USING ERRCODE = 'P0001';
    END IF;

    v_time := clock_timestamp();
    IF NOT EXISTS (
        SELECT 1
        FROM public.schedulers s
        WHERE s.post_id = p_post_id
          AND s.user_id = p_user_id
          AND s.profile_id = p_profile_id
          AND s.dispatch_cancelled_at IS NULL
          AND (
            s.trigger = 'cron'
            OR (
              s.trigger = 'date'
              AND s.run_date AT TIME ZONE 'America/Sao_Paulo'
                  > v_time + interval '30 minutes'
            )
          )
    ) THEN
        RAISE EXCEPTION 'NO_EDITABLE_FUTURE_SLOTS' USING ERRCODE = 'P0001';
    END IF;

    IF jsonb_typeof(p_snapshot) <> 'object'
       OR jsonb_typeof(p_snapshot->'texts') <> 'array'
       OR jsonb_typeof(p_snapshot->'medias') <> 'array'
       OR jsonb_typeof(p_snapshot->'product_ids') <> 'array'
    THEN
        RAISE EXCEPTION 'INVALID_REVISION_SNAPSHOT' USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.post_content_revisions (
        post_id, user_id, profile_id, snapshot, effective_after
    ) VALUES (
        p_post_id, p_user_id, p_profile_id, p_snapshot,
        v_time + interval '30 minutes'
    ) RETURNING id INTO v_revision_id;

    RETURN QUERY SELECT v_revision_id, v_time + interval '30 minutes';
END;
$$;
REVOKE ALL ON FUNCTION public.create_future_post_revision(integer, uuid, uuid, jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_future_post_revision(integer, uuid, uuid, jsonb)
  TO service_role;

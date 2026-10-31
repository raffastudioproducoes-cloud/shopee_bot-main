-- Reenvio manual de Threads: transação atômica, sem alterar dados de clientes
-- nem reutilizar a ocorrência de idempotência que terminou em unknown.
-- O scheduler atual recupera a nova ocorrência pending a cada minuto.
CREATE OR REPLACE FUNCTION public.enqueue_manual_post_retry(
    p_user_id UUID,
    p_profile_id UUID,
    p_post_id INTEGER,
    p_source_job_id UUID
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    source_job public.publish_jobs%ROWTYPE;
    latest_id UUID;
    retry_id UUID;
BEGIN
    -- O lock serializa dois cliques, e também a conciliação manual da mesma linha.
    SELECT * INTO source_job
      FROM public.publish_jobs
     WHERE id = p_source_job_id AND post_id = p_post_id
       AND user_id = p_user_id AND profile_id = p_profile_id
       AND network = 'threads'
     FOR UPDATE;
    IF NOT FOUND OR source_job.status <> 'unknown'
       OR COALESCE(source_job.last_error, '') LIKE 'USER_REPORTED_REMOVED; %'
       OR COALESCE(source_job.last_error, '') LIKE 'MANUAL_RETRY_REQUESTED; %'
    THEN
        RETURN NULL;
    END IF;

    -- Confere também o post: o RPC nunca pode criar ocorrência em outra conta,
    -- outro perfil, outra rede ou numa parte intermediária de uma thread.
    IF NOT EXISTS (
        SELECT 1 FROM public.posts p
         WHERE p.id = p_post_id AND p.user_id = p_user_id
           AND p.profile_id = p_profile_id AND p.post_id IS NULL
           AND COALESCE(p.network, 'threads') = 'threads'
    ) THEN
        RETURN NULL;
    END IF;

    SELECT id INTO latest_id
      FROM public.publish_jobs
     WHERE post_id = p_post_id AND user_id = p_user_id
       AND profile_id = p_profile_id
     ORDER BY created_at DESC, id DESC
     LIMIT 1;
    IF latest_id IS DISTINCT FROM p_source_job_id THEN
        RETURN NULL;
    END IF;

    -- Mantém o desfecho original como unknown (não inventa "failed").
    -- O marcador impede que outra aba confirme essa mesma ocorrência após
    -- o pedido; o novo job tem identidade/idempotência separada.
    UPDATE public.publish_jobs
       SET last_error = 'MANUAL_RETRY_REQUESTED; original=' ||
                        LEFT(COALESCE(source_job.last_error, ''), 400)
     WHERE id = p_source_job_id;

    INSERT INTO public.publish_jobs (
        scheduler_id, post_id, user_id, profile_id, network, idempotency_key
    ) VALUES (
        source_job.scheduler_id, source_job.post_id, source_job.user_id,
        source_job.profile_id, source_job.network, 'manual_retry:' || source_job.id::text
    )
    RETURNING id INTO retry_id;
    RETURN retry_id;
END;
$$;

-- Função em schema exposto, mas executável exclusivamente pelo serviço.
REVOKE ALL ON FUNCTION public.enqueue_manual_post_retry(UUID, UUID, INTEGER, UUID)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.enqueue_manual_post_retry(UUID, UUID, INTEGER, UUID)
    TO service_role;

-- Recibos publicos dos callbacks de exclusao de dados Meta/Threads.
-- Aditiva e idempotente: nao altera tabelas antigas nem depende do codigo
-- novo estar rodando em todos os processos ao mesmo tempo.
CREATE TABLE IF NOT EXISTS public.data_deletion_requests (
    id BIGSERIAL PRIMARY KEY,
    confirmation_code TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL CHECK (provider IN ('meta', 'threads')),
    external_user_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('received', 'completed', 'not_found')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_data_deletion_requests_provider_hash
    ON public.data_deletion_requests (provider, external_user_hash);

ALTER TABLE public.data_deletion_requests ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'data_deletion_requests'
          AND policyname = 'block_all_api'
    ) THEN
        CREATE POLICY "block_all_api"
            ON public.data_deletion_requests
            FOR ALL
            USING (false)
            WITH CHECK (false);
    END IF;
END $$;

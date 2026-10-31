-- Compatível com main/staging compartilhando o mesmo Supabase.
-- A coluna marca a fronteira irreversível: a partir daqui o provedor pode
-- ter recebido o envio, mesmo que o processo morra sem resposta.
ALTER TABLE public.publish_jobs
    ADD COLUMN IF NOT EXISTS external_started_at TIMESTAMPTZ;

-- Jobs iniciados por versões antigas não tinham esta instrumentação.
-- Preservá-los como incertos impede a recuperação duplicar publicações.
UPDATE public.publish_jobs
SET external_started_at = COALESCE(started_at, now())
WHERE status = 'running' AND external_started_at IS NULL;

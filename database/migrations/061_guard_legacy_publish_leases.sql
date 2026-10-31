-- Compatibilidade durante rollout: staging e main compartilham o banco.
-- Um worker antigo pode adquirir um job sem registrar external_started_at.
-- Somente claims cujo token foi gerado pela versão instrumentada podem
-- voltar para pending após expirar. UUID diferente ou NULL => unknown.
ALTER TABLE public.publish_jobs
    ADD COLUMN IF NOT EXISTS preflight_claim_token UUID;

-- NULL nos claims antigos é deliberado: jamais inferir retry seguro.

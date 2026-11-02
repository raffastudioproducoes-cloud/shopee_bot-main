-- F0: preparação ADITIVA e inerte para centralização de publicações.
-- A migração é idempotente e NÃO transfere, cancela nem executa agendas.
-- Todas as agendas anteriores (incluindo os 5 cron do staging) continuam
-- explicitamente no modo legacy. Ativação exige rollout separado.
ALTER TABLE public.schedulers
    ADD COLUMN IF NOT EXISTS dispatch_mode text NOT NULL DEFAULT 'legacy',
    ADD COLUMN IF NOT EXISTS dispatch_revision integer NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS dispatch_cancelled_at timestamptz;

ALTER TABLE public.schedulers
    DROP CONSTRAINT IF EXISTS schedulers_dispatch_mode_check;
ALTER TABLE public.schedulers
    ADD CONSTRAINT schedulers_dispatch_mode_check
        CHECK (dispatch_mode IN ('legacy', 'central'));

ALTER TABLE public.schedulers
    DROP CONSTRAINT IF EXISTS schedulers_dispatch_revision_check;
ALTER TABLE public.schedulers
    ADD CONSTRAINT schedulers_dispatch_revision_check
        CHECK (dispatch_revision >= 1);

CREATE INDEX IF NOT EXISTS idx_schedulers_central_active
    ON public.schedulers (id, dispatch_revision)
    WHERE dispatch_mode = 'central' AND dispatch_cancelled_at IS NULL;

-- Não alterar apscheduler_jobs*, publish_jobs, publication_claims ou RLS.
-- Central usa cancelamento lógico; DELETE físico em schedulers tem
-- ON DELETE CASCADE para publish_jobs e apagaria o histórico.

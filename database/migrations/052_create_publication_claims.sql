BEGIN;

-- Um lease por scheduler impede que duas instancias disparem o mesmo post
-- simultaneamente. O token protege uma execucao nova de um worker antigo.
CREATE TABLE IF NOT EXISTS public.publication_claims (
    scheduler_id UUID PRIMARY KEY REFERENCES public.schedulers(id) ON DELETE CASCADE,
    claim_token UUID NOT NULL,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;

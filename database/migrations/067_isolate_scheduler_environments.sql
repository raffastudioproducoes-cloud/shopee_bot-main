-- Compatível com os processos antigos: todas as agendas já existentes
-- pertencem à produção; apenas agendas novas do branch staging mudam de fila.
ALTER TABLE public.schedulers
    ADD COLUMN IF NOT EXISTS environment text NOT NULL DEFAULT 'production';

ALTER TABLE public.schedulers
    DROP CONSTRAINT IF EXISTS schedulers_environment_check;
ALTER TABLE public.schedulers
    ADD CONSTRAINT schedulers_environment_check
    CHECK (environment IN ('production', 'staging'));

CREATE INDEX IF NOT EXISTS idx_schedulers_environment
    ON public.schedulers (environment, id);

-- APScheduler 3.x não admite compartilhar um JobStore entre processos.
-- A tabela antiga continua exclusiva da main, sem mover/remover jobs.
CREATE TABLE IF NOT EXISTS public.apscheduler_jobs_staging (
    id varchar(191) PRIMARY KEY,
    next_run_time double precision,
    job_state bytea NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_apscheduler_jobs_staging_next_run_time
    ON public.apscheduler_jobs_staging (next_run_time);

ALTER TABLE public.apscheduler_jobs_staging ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.apscheduler_jobs_staging FROM PUBLIC, anon, authenticated;

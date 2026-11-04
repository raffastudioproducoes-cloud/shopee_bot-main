-- F4E: origem positiva e imutavel para legado/campanha no banco compartilhado.
-- Expand-only: nenhum produtor de campanha esta habilitado por esta migration.
-- Guard no PostgreSQL impede worker antigo de tratar campanha como legado.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE public.schedulers
  ADD COLUMN publication_origin text NOT NULL DEFAULT 'legacy';
ALTER TABLE public.schedulers
  ADD CONSTRAINT schedulers_publication_origin_check
  CHECK (publication_origin IN ('legacy', 'campaign'));

ALTER TABLE public.publish_jobs
  ADD COLUMN publication_origin text NOT NULL DEFAULT 'legacy';
ALTER TABLE public.publish_jobs
  ADD CONSTRAINT publish_jobs_publication_origin_check
  CHECK (publication_origin IN ('legacy', 'campaign'));

CREATE FUNCTION public.guard_publication_origin_f4e()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = '' AS $$
DECLARE
  v_schedule_origin text;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.publication_origin IS DISTINCT FROM OLD.publication_origin THEN
    RAISE EXCEPTION 'publication_origin_immutable' USING ERRCODE = '23514';
  END IF;

  IF TG_TABLE_NAME = 'publish_jobs' THEN
    SELECT s.publication_origin INTO v_schedule_origin
    FROM public.schedulers s WHERE s.id = NEW.scheduler_id FOR KEY SHARE;

    IF v_schedule_origin IS NULL OR NEW.publication_origin IS DISTINCT FROM v_schedule_origin THEN
      RAISE EXCEPTION 'publication_origin_parent_mismatch' USING ERRCODE = '23514';
    END IF;

    -- Campanha continua inerte: mesmo um worker antigo que ignore os novos
    -- filtros nao consegue reivindicar um job nem iniciar chamada externa.
    IF NEW.publication_origin = 'campaign' AND (
       NEW.status NOT IN ('pending', 'failed')
       OR NEW.external_started_at IS NOT NULL
       OR NEW.claim_token IS NOT NULL
       OR NEW.preflight_claim_token IS NOT NULL
    ) THEN
      RAISE EXCEPTION 'campaign_dispatch_not_enabled' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END; $$;

REVOKE ALL ON FUNCTION public.guard_publication_origin_f4e()
  FROM PUBLIC, anon, authenticated, service_role;

CREATE TRIGGER trg_guard_scheduler_publication_origin_f4e
BEFORE UPDATE OF publication_origin ON public.schedulers
FOR EACH ROW EXECUTE FUNCTION public.guard_publication_origin_f4e();

CREATE TRIGGER trg_guard_job_publication_origin_f4e
BEFORE INSERT OR UPDATE ON public.publish_jobs
FOR EACH ROW EXECUTE FUNCTION public.guard_publication_origin_f4e();

COMMIT;

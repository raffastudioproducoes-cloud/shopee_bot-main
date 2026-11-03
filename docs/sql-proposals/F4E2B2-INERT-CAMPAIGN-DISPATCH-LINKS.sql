-- F4E-2B2: proposta NÃO EXECUTÁVEL. NÃO aplicar no Supabase compartilhado.
-- Guardar APENAS em docs/sql-proposals, fora de database/migrations (boot).
-- Requer revisão PostgreSQL, compatibilidade da main e autorização específica.
-- Este contrato prova vínculo no INSERT, mas NÃO autoriza envio: status e
-- dispatch_enabled são imutavelmente inertes; service_role só pode ler.
-- O futuro claim, retry, recovery e pré-envio ainda precisam de guarda
-- transacional contra alterações de pais, downgrade, OAuth e cancelamento.
BEGIN;
SET LOCAL lock_timeout = '5s';

CREATE TABLE public.campaign_dispatch_links_f4e (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reservation_id uuid NOT NULL
    REFERENCES public.campaign_reservations_f4e(id) ON DELETE RESTRICT,
  occurrence_id uuid NOT NULL
    REFERENCES public.campaign_occurrences_f4e(id) ON DELETE RESTRICT,
  scheduler_id uuid NOT NULL
    REFERENCES public.schedulers(id) ON DELETE RESTRICT,
  publish_job_id uuid NOT NULL
    REFERENCES public.publish_jobs(id) ON DELETE RESTRICT,
  post_id integer NOT NULL
    REFERENCES public.posts(id) ON DELETE RESTRICT,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
  source_environment text NOT NULL CHECK (source_environment IN ('staging', 'production')),
  network text NOT NULL CHECK (network IN ('threads', 'facebook', 'instagram', 'tiktok')),
  status text NOT NULL DEFAULT 'inert' CHECK (status = 'inert'),
  dispatch_enabled boolean NOT NULL DEFAULT false CHECK (dispatch_enabled = false),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (occurrence_id, network),
  UNIQUE (publish_job_id)
);
CREATE INDEX campaign_dispatch_links_owner_idx
  ON public.campaign_dispatch_links_f4e (user_id, profile_id, reservation_id);

-- Conjunto completo de IDs é obrigatório e conferido dentro do banco.
-- Uma ocorrência pode ter UMA linha por rede; não confundir slots com posts.
CREATE FUNCTION public.guard_campaign_dispatch_link_f4e()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
BEGIN
  IF TG_OP <> 'INSERT' THEN
    RAISE EXCEPTION 'campaign_link_is_immutable' USING ERRCODE = '23514';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM public.campaign_occurrences_f4e occurrence
    JOIN public.campaign_reservations_f4e reservation
      ON reservation.id = occurrence.reservation_id
    JOIN public.schedulers schedule ON schedule.id = NEW.scheduler_id
    JOIN public.posts post ON post.id = NEW.post_id
    JOIN public.publish_jobs job ON job.id = NEW.publish_job_id
    JOIN public.profiles profile ON profile.id = NEW.profile_id
    WHERE occurrence.id = NEW.occurrence_id
      AND occurrence.reservation_id = NEW.reservation_id
      AND occurrence.status = 'planned'
      AND occurrence.dispatch_enabled = false
      AND reservation.id = NEW.reservation_id
      AND reservation.status = 'reserved_no_dispatch'
      AND reservation.dispatch_enabled = false
      AND reservation.user_id = NEW.user_id
      AND reservation.profile_id = NEW.profile_id
      AND profile.user_id = NEW.user_id
      AND schedule.user_id = NEW.user_id
      AND schedule.profile_id = NEW.profile_id
      AND schedule.post_id = NEW.post_id
      AND schedule.environment = NEW.source_environment
      AND schedule.dispatch_mode = 'central'
      AND schedule.dispatch_cancelled_at IS NULL
      AND post.user_id = NEW.user_id
      AND post.profile_id = NEW.profile_id
      AND job.scheduler_id = NEW.scheduler_id
      AND job.user_id = NEW.user_id
      AND job.profile_id = NEW.profile_id
      AND job.post_id = NEW.post_id
      AND job.network = NEW.network
      AND job.status = 'pending'
      AND job.external_started_at IS NULL
  ) THEN
    RAISE EXCEPTION 'campaign_link_identity_mismatch' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_guard_campaign_dispatch_link_f4e
  BEFORE INSERT OR UPDATE OR DELETE ON public.campaign_dispatch_links_f4e
  FOR EACH ROW EXECUTE FUNCTION public.guard_campaign_dispatch_link_f4e();

ALTER TABLE public.campaign_dispatch_links_f4e ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.campaign_dispatch_links_f4e
  FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON public.campaign_dispatch_links_f4e TO service_role;
REVOKE ALL ON FUNCTION public.guard_campaign_dispatch_link_f4e()
  FROM PUBLIC, anon, authenticated, service_role;

COMMENT ON TABLE public.campaign_dispatch_links_f4e IS
  'F4E-2B2 inerte: nenhum INSERT autorizado; não vincular a scheduler nem publish_jobs até gates futuros.';
COMMIT;

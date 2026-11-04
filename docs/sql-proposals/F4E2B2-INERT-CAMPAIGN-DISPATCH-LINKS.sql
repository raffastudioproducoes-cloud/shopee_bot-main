-- F4E-2B2: proposta NÃO EXECUTÁVEL. NÃO aplicar no Supabase compartilhado.
-- Guardar APENAS em docs/sql-proposals, fora de database/migrations (boot).
-- Requer revisão PostgreSQL, compatibilidade da main e autorização específica.
-- Este contrato prova vínculo no INSERT, mas NÃO autoriza envio: status e
-- dispatch_enabled são imutavelmente inertes; service_role só pode ler.
-- O futuro claim, retry, recovery e pré-envio ainda precisam de guarda
-- transacional contra downgrade EFETIVO (nunca pedido durante ciclo pago), OAuth e cancelamento.
-- F4E-2B3: chaves compostas/FKs RESTRICT preservam identidade dos pais mesmo
-- sob concorrencia/REPEATABLE READ; triggers de consulta isolados nao bastam.
-- Indices aditivos custam locks/espaco: revisar antes de qualquer DDL real.
BEGIN;
SET LOCAL lock_timeout = '5s';

-- Somente identidade, NAO status, cancelamento, lease ou conteudo mutavel.
-- Todas incluem PK: nao introduzem nova unicidade comercial para legado.
CREATE UNIQUE INDEX campaign_link_profile_identity_f4e
  ON public.profiles (id, user_id);
CREATE UNIQUE INDEX campaign_link_reservation_identity_f4e
  ON public.campaign_reservations_f4e (id, user_id, profile_id);
CREATE UNIQUE INDEX campaign_link_occurrence_identity_f4e
  ON public.campaign_occurrences_f4e (id, reservation_id);
CREATE UNIQUE INDEX campaign_link_schedule_identity_f4e
  ON public.schedulers (id, post_id, user_id, profile_id, environment);
CREATE UNIQUE INDEX campaign_link_post_identity_f4e
  ON public.posts (id, user_id, profile_id, network);
CREATE UNIQUE INDEX campaign_link_job_identity_f4e
  ON public.publish_jobs (id, scheduler_id, post_id, user_id, profile_id, network);

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
  UNIQUE (publish_job_id),
  FOREIGN KEY (profile_id, user_id)
    REFERENCES public.profiles (id, user_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (reservation_id, user_id, profile_id)
    REFERENCES public.campaign_reservations_f4e (id, user_id, profile_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (occurrence_id, reservation_id)
    REFERENCES public.campaign_occurrences_f4e (id, reservation_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (scheduler_id, post_id, user_id, profile_id, source_environment)
    REFERENCES public.schedulers (id, post_id, user_id, profile_id, environment)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (post_id, user_id, profile_id, network)
    REFERENCES public.posts (id, user_id, profile_id, network)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (publish_job_id, scheduler_id, post_id, user_id, profile_id, network)
    REFERENCES public.publish_jobs (id, scheduler_id, post_id, user_id, profile_id, network)
    ON UPDATE RESTRICT ON DELETE RESTRICT
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
  -- Ordem deterministica entre os pais deste contrato. Locks estabilizam a
  -- validacao inicial de status; FKs compostas sao a autoridade permanente
  -- para identidade, incluindo snapshots de transacao antigos.
  PERFORM 1 FROM public.campaign_occurrences_f4e WHERE id = NEW.occurrence_id FOR UPDATE;
  PERFORM 1 FROM public.campaign_reservations_f4e WHERE id = NEW.reservation_id FOR UPDATE;
  PERFORM 1 FROM public.posts WHERE id = NEW.post_id FOR UPDATE;
  PERFORM 1 FROM public.profiles WHERE id = NEW.profile_id FOR UPDATE;
  PERFORM 1 FROM public.publish_jobs WHERE id = NEW.publish_job_id FOR UPDATE;
  PERFORM 1 FROM public.schedulers WHERE id = NEW.scheduler_id FOR UPDATE;
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
      AND post.network = NEW.network
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

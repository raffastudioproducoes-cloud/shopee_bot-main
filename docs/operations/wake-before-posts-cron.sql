-- Despertar do site de PRODUÇÃO antes das publicações (decisão de Rafa, 11/11/2026).
-- Aplicado direto no Supabase (banco compartilhado). NÃO faz parte das migrations do app.
--
-- Regra: o cron roda a cada minuto, mas é só uma CONSULTA no banco. O site (Render) só é chamado quando existe
-- publicação do ambiente 'production' nos próximos 4 minutos (ou atrasada há menos de 1 hora) — ou seja,
-- o ping chega entre 3 e 4 minutos antes. Publicações do ambiente 'staging' nunca disparam chamada.
-- Cada chamada vira uma linha em public.admin_wake_log (status ok/error/unanswered + código HTTP).
-- A manutenção do site vivo continua no cron de 12 em 12 minutos (public.admin_uptime_tick, log em admin_uptime_checks).

CREATE TABLE IF NOT EXISTS public.admin_wake_log (
  id           bigserial PRIMARY KEY,
  requested_at timestamptz NOT NULL DEFAULT now(),
  reason       text        NOT NULL,
  due_at       timestamptz,
  items        integer,
  request_id   bigint,
  status       text        NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','ok','error','unanswered')),
  http_status  integer,
  checked_at   timestamptz
);
CREATE INDEX IF NOT EXISTS idx_admin_wake_log_requested ON public.admin_wake_log (requested_at DESC);
ALTER TABLE public.admin_wake_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.admin_wake_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.admin_wake_log TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.admin_wake_log_id_seq TO service_role;

-- Faz a chamada HTTP e registra no log.
CREATE OR REPLACE FUNCTION app_internal.wake_ping(p_reason text, p_due timestamptz, p_items integer)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $fn$
DECLARE
  v_url text; v_secret text; v_req bigint;
BEGIN
  SELECT decrypted_secret INTO v_url FROM vault.decrypted_secrets WHERE name = 'auto_orbital_wake_url';
  SELECT decrypted_secret INTO v_secret FROM vault.decrypted_secrets WHERE name = 'auto_orbital_wake_secret';
  IF v_url IS NULL OR v_secret IS NULL OR left(v_url, 8) <> 'https://' THEN
    INSERT INTO public.admin_wake_log (reason, due_at, items, status, checked_at)
    VALUES (p_reason || ':configuracao_ausente_ou_invalida', p_due, p_items, 'error', now());
    RETURN;
  END IF;
  v_req := net.http_post(
    url := v_url, body := '{}'::jsonb,
    headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_secret),
    timeout_milliseconds := 90000);
  INSERT INTO public.admin_wake_log (reason, due_at, items, request_id) VALUES (p_reason, p_due, p_items, v_req);
END;
$fn$;

-- Roda a cada minuto (só consulta). Chama o site apenas quando há publicação de produção próxima ou atrasada.
CREATE OR REPLACE FUNCTION app_internal.wake_dispatch_if_needed()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $fn$
DECLARE
  v_lead constant interval := interval '4 minutes';
  v_due timestamptz; v_items integer;
BEGIN
  -- Fecha o log das chamadas anteriores com a resposta HTTP.
  UPDATE public.admin_wake_log l
     SET status = CASE WHEN r.timed_out OR r.error_msg IS NOT NULL THEN 'error'
                       WHEN r.status_code BETWEEN 200 AND 299 THEN 'ok' ELSE 'error' END,
         http_status = r.status_code, checked_at = now()
    FROM net._http_response r WHERE l.request_id = r.id AND l.status = 'pending';
  UPDATE public.admin_wake_log SET status = 'unanswered', checked_at = now()
   WHERE status = 'pending' AND request_id IS NOT NULL AND requested_at < now() - interval '5 minutes';
  DELETE FROM public.admin_wake_log WHERE requested_at < now() - interval '30 days';

  SELECT min(d.at), count(*) INTO v_due, v_items FROM (
    -- Agendamentos do APScheduler (ambiente de produção).
    SELECT to_timestamp(j.next_run_time) AS at
      FROM public.apscheduler_jobs j JOIN public.schedulers s ON j.id = s.id::text
     WHERE s.environment = 'production'
       AND s.func IN ('bot_post','bot_post_x','bot_post_facebook','bot_post_instagram','bot_post_tiktok')
       AND j.next_run_time IS NOT NULL
       AND j.next_run_time <= extract(epoch FROM now() + v_lead)
       AND j.next_run_time >= extract(epoch FROM now() - interval '1 hour')
    UNION ALL
    -- Horários de campanha de produção.
    SELECT s.planned_at
      FROM public.campaign_network_slots_f4e s JOIN public.publish_jobs q ON q.id = s.publish_job_id
     WHERE s.source_environment = 'production' AND q.status = 'pending'
       AND s.planned_at <= now() + v_lead AND s.planned_at >= now() - interval '1 hour'
    UNION ALL
    -- Fila recente ou envio preso (recuperação) de agendamentos de produção.
    SELECT coalesce(q.locked_at, q.created_at)
      FROM public.publish_jobs q
     WHERE q.publication_origin = 'legacy'
       AND EXISTS (SELECT 1 FROM public.schedulers sc WHERE sc.id = q.scheduler_id AND sc.environment = 'production')
       AND ((q.status = 'pending' AND q.created_at >= now() - interval '1 hour')
         OR (q.status = 'running' AND q.locked_at < now() - interval '10 minutes'))
  ) d;

  IF v_items = 0 THEN RETURN; END IF;
  -- Não repete a chamada em menos de 5 minutos (a 1ª chega 3 a 4 min antes; a 2ª só se a publicação atrasar).
  IF EXISTS (SELECT 1 FROM public.admin_wake_log WHERE requested_at > now() - interval '5 minutes') THEN RETURN; END IF;
  PERFORM app_internal.wake_ping('publicacao_de_producao_em_ate_4min', v_due, v_items);
END;
$fn$;

SELECT cron.alter_job(job_id := 1, schedule := '* * * * *');

-- ROLLBACK (versão anterior): recriar app_internal.wake_dispatch_if_needed() com a definição guardada em
-- docs/operations/wake-before-posts-cron.rollback.sql e:  SELECT cron.alter_job(job_id := 1, schedule := '*/2 * * * *');

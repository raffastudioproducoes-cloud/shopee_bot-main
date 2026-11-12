-- Versão ANTERIOR do despertar (cron */2, chamava o site sempre que houvesse qualquer publish_job pendente).
-- Guardada em 11/11/2026 antes da troca. Para reverter: rodar este arquivo e
--   SELECT cron.alter_job(job_id := 1, schedule := '*/2 * * * *');
CREATE OR REPLACE FUNCTION app_internal.wake_dispatch_if_needed()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
DECLARE
    v_url text;
    v_secret text;
BEGIN
    IF NOT (
        EXISTS (
            SELECT 1 FROM public.apscheduler_jobs AS j
            JOIN public.schedulers AS s ON j.id = s.id::text
            WHERE s.func IN ('bot_post','bot_post_x','bot_post_facebook','bot_post_instagram','bot_post_tiktok')
              AND j.next_run_time IS NOT NULL
              AND j.next_run_time <= EXTRACT(EPOCH FROM (now() + interval '5 minutes'))
        )
        OR EXISTS (
            SELECT 1 FROM public.publish_jobs AS q
            WHERE q.status = 'pending'
               OR (q.status = 'running' AND q.locked_at < now() - interval '10 minutes')
        )
    ) THEN
        RETURN;
    END IF;
    SELECT decrypted_secret INTO v_url FROM vault.decrypted_secrets WHERE name = 'auto_orbital_wake_url';
    SELECT decrypted_secret INTO v_secret FROM vault.decrypted_secrets WHERE name = 'auto_orbital_wake_secret';
    IF v_url IS NULL OR v_secret IS NULL THEN
        RAISE EXCEPTION 'Configuracao de despertar ausente';
    END IF;
    IF left(v_url, 8) <> 'https://' THEN
        RAISE EXCEPTION 'Endpoint de despertar deve usar HTTPS';
    END IF;
    PERFORM net.http_post(
        url := v_url, body := '{}'::jsonb,
        headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || v_secret),
        timeout_milliseconds := 90000);
END;
$function$;

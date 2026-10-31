-- Agregação de envios concluídos para gráficos, sem copiar dados para outra tabela.
-- Mesmas janelas móveis e escopo conta+perfil do GET /analytics/summary.
CREATE OR REPLACE FUNCTION public.analytics_daily_job_counts(
    p_user_id UUID,
    p_profile_id UUID,
    p_days INTEGER,
    p_network TEXT DEFAULT NULL
)
RETURNS TABLE (day DATE, network TEXT, status TEXT, total BIGINT)
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = ''
AS $function$
    SELECT
        (j.finished_at AT TIME ZONE 'UTC')::DATE AS day,
        j.network,
        j.status,
        count(*)::BIGINT AS total
    FROM public.publish_jobs AS j
    WHERE p_days IN (7, 30, 90)
      AND (p_network IS NULL OR (p_network IN ('threads','facebook','instagram','tiktok','x') AND j.network = p_network))
      AND EXISTS (
          SELECT 1
          FROM public.profiles AS p
          WHERE p.id = p_profile_id AND p.user_id = p_user_id
      )
      AND j.user_id = p_user_id
      AND j.profile_id = p_profile_id
      AND j.finished_at >= now() - make_interval(days => p_days)
      AND j.status IN ('succeeded', 'failed', 'unknown')
      AND j.network IN ('threads', 'facebook', 'instagram', 'tiktok', 'x')
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
$function$;

REVOKE ALL ON FUNCTION public.analytics_daily_job_counts(UUID, UUID, INTEGER, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.analytics_daily_job_counts(UUID, UUID, INTEGER, TEXT)
    TO service_role;

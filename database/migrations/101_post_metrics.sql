-- 12/11/2026: metricas por postagem com historico + redirecionador proprio de cliques.
-- Aditiva e idempotente. Banco compartilhado staging/producao: so tabelas e uma funcao
-- novas; publication_insights continua igual e o codigo da main (3.18.0) nao le nem
-- escreve nada daqui. Navegador nunca le estas tabelas: RLS fechada, apenas service_role.
-- LGPD: nenhuma linha guarda IP, user agent, token de rede ou resposta bruta da API.
--
-- Reversao (somente depois de voltar o codigo que usa as tabelas):
--   DROP FUNCTION IF EXISTS public.record_post_link_click(text);
--   DROP TABLE IF EXISTS public.post_link_click_days;
--   DROP TABLE IF EXISTS public.post_link_clicks;
--   DROP TABLE IF EXISTS public.post_metrics;
--   DELETE FROM migrations WHERE name = '101_post_metrics.sql';
BEGIN;
SET LOCAL lock_timeout = '10s';

-- Historico append-only: uma linha por coleta (sucesso ou falha) de um post publicado.
-- Campo indisponivel na rede = NULL (nunca 0). Retencao: sem expurgo (>= 365 dias).
CREATE TABLE IF NOT EXISTS public.post_metrics (
  id bigserial PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  profile_id uuid,
  post_id integer REFERENCES public.posts(id) ON DELETE CASCADE,
  publish_job_id uuid REFERENCES public.publish_jobs(id) ON DELETE CASCADE,
  network text NOT NULL CHECK (char_length(network) BETWEEN 1 AND 32),
  external_id text CHECK (external_id IS NULL OR char_length(external_id) <= 512),
  collected_at timestamptz NOT NULL DEFAULT now(),
  window_label text NOT NULL DEFAULT 'latest'
    CHECK (window_label IN ('1h', '24h', '7d', '30d', '90d', 'latest')),
  views bigint CHECK (views IS NULL OR views >= 0),
  reach bigint CHECK (reach IS NULL OR reach >= 0),
  likes bigint CHECK (likes IS NULL OR likes >= 0),
  comments bigint CHECK (comments IS NULL OR comments >= 0),
  shares bigint CHECK (shares IS NULL OR shares >= 0),
  saves bigint CHECK (saves IS NULL OR saves >= 0),
  clicks bigint CHECK (clicks IS NULL OR clicks >= 0),
  extra jsonb NOT NULL DEFAULT '{}'::jsonb,
  source text CHECK (source IS NULL OR char_length(source) <= 64),
  status text NOT NULL CHECK (char_length(status) BETWEEN 1 AND 40),
  error text CHECK (error IS NULL OR char_length(error) <= 200)
);
CREATE INDEX IF NOT EXISTS idx_post_metrics_user_network_time
  ON public.post_metrics (user_id, network, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_post_metrics_post_network_time
  ON public.post_metrics (post_id, network, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_post_metrics_job_time
  ON public.post_metrics (publish_job_id, collected_at DESC);

-- Um link opaco por (envio, destino). O destino so vem daqui, nunca da URL do clique.
CREATE TABLE IF NOT EXISTS public.post_link_clicks (
  id bigserial PRIMARY KEY,
  token text NOT NULL UNIQUE CHECK (token ~ '^[A-Za-z0-9_-]{22,64}$'),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  profile_id uuid,
  post_id integer REFERENCES public.posts(id) ON DELETE CASCADE,
  publish_job_id uuid REFERENCES public.publish_jobs(id) ON DELETE CASCADE,
  network text NOT NULL CHECK (char_length(network) BETWEEN 1 AND 32),
  target_url text NOT NULL CHECK (target_url LIKE 'https://%' AND char_length(target_url) <= 2048),
  created_at timestamptz NOT NULL DEFAULT now(),
  clicks bigint NOT NULL DEFAULT 0 CHECK (clicks >= 0),
  last_click_at timestamptz,
  CONSTRAINT post_link_clicks_job_target UNIQUE (publish_job_id, target_url)
);
CREATE INDEX IF NOT EXISTS idx_post_link_clicks_user
  ON public.post_link_clicks (user_id, network, created_at DESC);

-- Contagem agregada por dia (UTC), sem nenhum dado de quem clicou.
CREATE TABLE IF NOT EXISTS public.post_link_click_days (
  token text NOT NULL REFERENCES public.post_link_clicks(token) ON DELETE CASCADE,
  day date NOT NULL,
  clicks bigint NOT NULL DEFAULT 0 CHECK (clicks >= 0),
  PRIMARY KEY (token, day)
);

-- Incremento atomico; devolve o destino guardado ou NULL para token inexistente.
CREATE OR REPLACE FUNCTION public.record_post_link_click(p_token text)
RETURNS text
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
  v_url text;
BEGIN
  UPDATE public.post_link_clicks
     SET clicks = clicks + 1, last_click_at = now()
   WHERE token = p_token
  RETURNING target_url INTO v_url;
  IF v_url IS NULL THEN
    RETURN NULL;
  END IF;
  INSERT INTO public.post_link_click_days (token, day, clicks)
  VALUES (p_token, (now() AT TIME ZONE 'UTC')::date, 1)
  ON CONFLICT (token, day) DO UPDATE SET clicks = public.post_link_click_days.clicks + 1;
  RETURN v_url;
END $$;

ALTER TABLE public.post_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_link_clicks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_link_click_days ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.post_metrics, public.post_link_clicks, public.post_link_click_days
  FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE public.post_metrics, public.post_link_clicks, public.post_link_click_days TO service_role;
REVOKE ALL ON SEQUENCE public.post_metrics_id_seq, public.post_link_clicks_id_seq
  FROM PUBLIC, anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.post_metrics_id_seq, public.post_link_clicks_id_seq TO service_role;
REVOKE ALL ON FUNCTION public.record_post_link_click(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_post_link_click(text) TO service_role;

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['post_metrics', 'post_link_clicks', 'post_link_click_days'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = t
                   AND policyname = 'block_all_api') THEN
      EXECUTE format('CREATE POLICY block_all_api ON public.%I FOR ALL USING (false) WITH CHECK (false)', t);
    END IF;
  END LOOP;
END $$;

COMMENT ON TABLE public.post_metrics IS
  'Historico append-only de coletas por publicacao confirmada; NULL = metrica indisponivel.';
COMMENT ON TABLE public.post_link_clicks IS
  'Links opacos do redirecionador /r/{token}; destino somente Shopee HTTPS; sem IP/UA.';

COMMIT;

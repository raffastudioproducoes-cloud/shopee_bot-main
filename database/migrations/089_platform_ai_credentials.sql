-- IA fornecida pela plataforma (administrada no backend, nunca pelo cliente).
-- Migração aditiva e retrocompatível com main 3.3.0 no mesmo Supabase.
-- A chave já cadastrada pelo ADMIN é copiada cifrada, sem decifrar no SQL.
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.platform_ai_credentials (
    environment text NOT NULL CHECK (environment IN ('production', 'staging')),
    provider text NOT NULL CHECK (provider IN ('gemini', 'openai', 'anthropic')),
    secret text,
    model text,
    status boolean NOT NULL DEFAULT false,
    check_state text CHECK (check_state IN ('testing', 'ok', 'error') OR check_state IS NULL),
    check_message text,
    checked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (environment, provider)
);

CREATE TABLE IF NOT EXISTS public.platform_ai_settings (
    environment text PRIMARY KEY CHECK (environment IN ('production', 'staging')),
    active_provider text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (environment, active_provider)
        REFERENCES public.platform_ai_credentials(environment, provider)
);

ALTER TABLE public.platform_ai_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_ai_settings ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
                   AND tablename='platform_ai_credentials' AND policyname='block_all_api') THEN
        CREATE POLICY block_all_api ON public.platform_ai_credentials
            FOR ALL USING (false) WITH CHECK (false);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
                   AND tablename='platform_ai_settings' AND policyname='block_all_api') THEN
        CREATE POLICY block_all_api ON public.platform_ai_settings
            FOR ALL USING (false) WITH CHECK (false);
    END IF;
END $$;

REVOKE ALL ON TABLE public.platform_ai_credentials, public.platform_ai_settings
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.platform_ai_credentials, public.platform_ai_settings TO service_role;

-- Se houver mais de um ADMIN, prioriza a credencial ativa mais recente de
-- cada provedor. Nunca copia chave de USER, nem sobrescreve configuração nova.
INSERT INTO public.platform_ai_credentials
    (environment, provider, secret, model, status, updated_at)
SELECT DISTINCT ON (environment, c.provider) environment, c.provider, c.secret, c.model, true,
       COALESCE(c.updated_at, now())
  FROM (VALUES ('production'), ('staging')) AS environments(environment)
  CROSS JOIN public.ai_credentials c
  JOIN public.users u ON u.id = c.user_id
 WHERE u.access = 'ADMIN' AND c.status IS TRUE AND c.secret IS NOT NULL
 ORDER BY environment, c.provider, c.updated_at DESC NULLS LAST, c.id DESC
ON CONFLICT (environment, provider) DO NOTHING;

-- A configuração inicial seleciona o último provedor ADMIN salvo (Gemini
-- na instância verificada em 07/11/2026). Sem chave, o serviço fica inativo.
INSERT INTO public.platform_ai_settings (environment, active_provider)
SELECT environments.environment,
       (SELECT provider FROM public.platform_ai_credentials credentials
         WHERE credentials.environment = environments.environment
           AND status IS TRUE AND secret IS NOT NULL
         ORDER BY updated_at DESC, provider LIMIT 1)
  FROM (VALUES ('production'), ('staging')) AS environments(environment)
ON CONFLICT (environment) DO NOTHING;

NOTIFY pgrst, 'reload schema';

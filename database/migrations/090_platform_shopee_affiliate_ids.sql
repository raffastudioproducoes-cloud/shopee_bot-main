-- Catálogo da plataforma + identificador de afiliado individual por conta.
-- EXPAND retrocompatível: não remove nem altera as chaves legadas.
-- Banco único staging/produção: a API global é isolada por environment.
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.platform_shopee_credentials (
    environment text PRIMARY KEY CHECK (environment IN ('production', 'staging')),
    app_id text,
    secret text,
    status boolean NOT NULL DEFAULT false,
    check_state text CHECK (check_state IN ('ok', 'error', 'testing') OR check_state IS NULL),
    check_message text,
    checked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.shopee_affiliate_accounts (
    user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    affiliate_id text NOT NULL CHECK (affiliate_id ~ '^[0-9]{5,20}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.platform_shopee_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shopee_affiliate_accounts ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                   AND tablename = 'platform_shopee_credentials' AND policyname = 'block_all_api') THEN
        CREATE POLICY block_all_api ON public.platform_shopee_credentials
            FOR ALL USING (false) WITH CHECK (false);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                   AND tablename = 'shopee_affiliate_accounts' AND policyname = 'block_all_api') THEN
        CREATE POLICY block_all_api ON public.shopee_affiliate_accounts
            FOR ALL USING (false) WITH CHECK (false);
    END IF;
END $$;

REVOKE ALL ON TABLE public.platform_shopee_credentials, public.shopee_affiliate_accounts
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.platform_shopee_credentials, public.shopee_affiliate_accounts TO service_role;

-- Copia sem descriptografar a chave Shopee mais recente de ADMIN; não
-- seleciona nenhum segredo de USER, não sobrepõe nova configuração.
INSERT INTO public.platform_shopee_credentials
    (environment, app_id, secret, status, updated_at)
SELECT DISTINCT ON (environment) environment, c.app_id, c.secret, true,
       COALESCE(c.updated_at, now())
  FROM (VALUES ('production'), ('staging')) AS environments(environment)
  CROSS JOIN public.shopee_credentials c
  JOIN public.users u ON u.id = c.user_id
 WHERE u.access = 'ADMIN' AND c.status IS TRUE
   AND c.app_id IS NOT NULL AND c.secret IS NOT NULL
 ORDER BY environment, c.updated_at DESC NULLS LAST, c.id DESC
ON CONFLICT (environment) DO NOTHING;

NOTIFY pgrst, 'reload schema';

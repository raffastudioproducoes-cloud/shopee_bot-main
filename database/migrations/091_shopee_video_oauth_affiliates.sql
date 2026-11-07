-- OAuth Shopee Vídeo para CRIADORES AFILIADOS (auth_type=user), separado de
-- Shopee Affiliate GraphQL. EXPAND: sem alteração de tabelas existentes.
-- Staging/main compartilham este banco; credenciais isoladas por environment.
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.platform_shopee_video_apps (
    environment text PRIMARY KEY CHECK (environment IN ('production', 'staging')),
    partner_id bigint NOT NULL CHECK (partner_id > 0),
    partner_key text NOT NULL, -- Fernet cifrado pela aplicação
    sandbox boolean NOT NULL DEFAULT true,
    enabled boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.shopee_video_authorizations (
    environment text NOT NULL CHECK (environment IN ('production', 'staging')),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    partner_id bigint NOT NULL CHECK (partner_id > 0),
    shopee_user_id bigint NOT NULL CHECK (shopee_user_id > 0),
    access_token text NOT NULL, -- Fernet cifrado, nunca devolvido pela API
    refresh_token text NOT NULL, -- Fernet cifrado, rotacionado na renovação
    expires_at timestamptz NOT NULL,
    refresh_expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (environment, user_id, profile_id)
);

CREATE INDEX IF NOT EXISTS shopee_video_authorizations_shopee_user_idx
    ON public.shopee_video_authorizations (environment, shopee_user_id);

ALTER TABLE public.platform_shopee_video_apps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shopee_video_authorizations ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                   AND tablename = 'platform_shopee_video_apps' AND policyname = 'block_all_api') THEN
        CREATE POLICY block_all_api ON public.platform_shopee_video_apps
            FOR ALL USING (false) WITH CHECK (false);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                   AND tablename = 'shopee_video_authorizations' AND policyname = 'block_all_api') THEN
        CREATE POLICY block_all_api ON public.shopee_video_authorizations
            FOR ALL USING (false) WITH CHECK (false);
    END IF;
END $$;

REVOKE ALL ON TABLE public.platform_shopee_video_apps,
    public.shopee_video_authorizations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.platform_shopee_video_apps, public.shopee_video_authorizations TO service_role;

NOTIFY pgrst, 'reload schema';

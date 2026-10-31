-- As tabelas abaixo usam RLS com policy block_all_api (USING false),
-- mas ainda tinham GRANTs automaticos para anon/authenticated.
-- TRUNCATE, REFERENCES e TRIGGER nao sao operacoes filtradas por RLS.
-- Mantem intocados SELECT/INSERT/UPDATE/DELETE ate validacao de clientes.
-- Revogacao ja aplicada e verificada no Supabase autovendas em 31/10/2026.
SET LOCAL lock_timeout = '10s';

REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE
    public.activities,
    public.activity_types,
    public.ai_credentials,
    public.apscheduler_jobs,
    public.audit_events,
    public.credential_checks,
    public.data_deletion_requests,
    public.facebook_credentials,
    public.instagram_credentials,
    public.kwai_credentials,
    public.medias,
    public.migrations,
    public.posts,
    public.posts_medias,
    public.posts_products,
    public.product_lists,
    public.product_lists_products,
    public.products,
    public.profiles,
    public.request_logs,
    public.schedulers,
    public.shopee_credentials,
    public.threads_credentials,
    public.tiktok_credentials,
    public.users,
    public.x_credentials
FROM anon, authenticated;

-- App-scoped Facebook user id returned by GET /me during Meta OAuth.
-- Nullable so old app versions and old connected accounts keep working.
DROP INDEX IF EXISTS public.uq_data_deletion_requests_provider_hash;

ALTER TABLE public.facebook_credentials
    ADD COLUMN IF NOT EXISTS fb_user_id TEXT;

ALTER TABLE public.instagram_credentials
    ADD COLUMN IF NOT EXISTS fb_user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_facebook_credentials_fb_user_id
    ON public.facebook_credentials (fb_user_id);

CREATE INDEX IF NOT EXISTS idx_instagram_credentials_fb_user_id
    ON public.instagram_credentials (fb_user_id);

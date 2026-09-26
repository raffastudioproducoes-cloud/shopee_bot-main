-- OAuth Authorization Code flow (TikTok for Developers, Content Posting API):
-- app_id/secret (Client Key/Secret) já existiam; estas colunas guardam o
-- token do USUÁRIO obtido depois que ele autoriza o app (ver apis/tiktok.py
-- e api/tiktok_oauth.py).
ALTER TABLE tiktok_credentials
    ADD COLUMN IF NOT EXISTS user_access_token TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS refresh_token TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS open_id TEXT DEFAULT NULL;

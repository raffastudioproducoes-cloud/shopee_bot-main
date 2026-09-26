-- Instagram: publicação via Graph API precisa de um user_access_token
-- (Facebook Login for Business, com escopos instagram_basic +
-- instagram_content_publish + pages_show_list) e do id da conta
-- Instagram Business/Creator vinculada à Página do Facebook do usuário.
-- app_id/secret continuam sendo as credenciais do App Meta (client
-- credentials, já existentes); estas duas colunas guardam o resultado
-- do fluxo OAuth (ver api/instagram_oauth.py).
ALTER TABLE instagram_credentials
    ADD COLUMN IF NOT EXISTS user_access_token TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS ig_user_id TEXT DEFAULT NULL;

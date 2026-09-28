-- Facebook migra pro modelo de app único (Login do Facebook, mesmo app
-- Meta já usado por INSTAGRAM_APP_ID/SECRET, ver api/facebook_oauth.py) —
-- app_id/secret per-user ficam obsoletos (linhas antigas continuam lidas
-- pelo caminho legado em scheduler/bot_post_facebook.py até serem
-- reconectadas). page_access_token é o token JÁ escopado pra Página
-- específica (resolvido via /me/accounts do usuário autenticado, não
-- mais derivado de um App Token que só enxerga páginas do próprio app).
ALTER TABLE facebook_credentials
    ADD COLUMN IF NOT EXISTS page_name TEXT,
    ADD COLUMN IF NOT EXISTS page_access_token TEXT;

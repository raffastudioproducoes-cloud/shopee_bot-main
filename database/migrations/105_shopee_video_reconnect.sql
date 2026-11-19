-- 19/11/2026: estado de reconexão da Shopee Vídeo (refresh_token de uso único).
-- Quando a Shopee recusa o refresh ou a gravação do par novo falha, a
-- autorização fica marcada para o usuário reconectar; o publicador e a rotina
-- de renovação ignoram linhas marcadas. Colunas aditivas com padrão constante
-- (sem reescrita da tabela); o código anterior lê colunas explícitas e ignora
-- estas. Idempotente: roda no boot de staging e produção (Supabase compartilhado).
-- RLS e grants reafirmados no mesmo padrão da 091 (sem mudança efetiva).
--
-- Reversão (somente depois de voltar o código que usa as colunas):
--   ALTER TABLE public.shopee_video_authorizations DROP COLUMN IF EXISTS reconnect_reason;
--   ALTER TABLE public.shopee_video_authorizations DROP COLUMN IF EXISTS needs_reconnect;
--   DELETE FROM migrations WHERE name = '105_shopee_video_reconnect.sql';
BEGIN;
SET LOCAL lock_timeout = '10s';

ALTER TABLE public.shopee_video_authorizations
  ADD COLUMN IF NOT EXISTS needs_reconnect boolean NOT NULL DEFAULT false;
ALTER TABLE public.shopee_video_authorizations
  ADD COLUMN IF NOT EXISTS reconnect_reason text
    CHECK (reconnect_reason IS NULL OR char_length(reconnect_reason) <= 200);

ALTER TABLE public.shopee_video_authorizations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.shopee_video_authorizations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.shopee_video_authorizations TO service_role;

COMMIT;

NOTIFY pgrst, 'reload schema';

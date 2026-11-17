-- 17/11/2026: escolhas do usuário para publicar no TikTok (Content Sharing Guidelines).
-- Coluna aditiva e anulável na head do post: modo (direto/rascunho), privacidade,
-- interações, divulgação comercial, rótulo de IA e o aceite da declaração, gravados
-- no momento em que o usuário cria/agenda. O scheduler envia exatamente isso ao
-- TikTok; NULL = post antigo sem consentimento registrado, que falha com
-- "Reconfirme as opções do TikTok" e nunca publica com valores inventados.
-- Campanhas guardam as mesmas escolhas no JSON dos itens (campaign_drafts.items),
-- que o snapshot da reserva congela; sem coluna nova para elas.
-- Idempotente; o código anterior (main) lê colunas explícitas e ignora esta.
-- RLS e grants da tabela posts seguem iguais.
--
-- Reversão (somente depois de voltar o código que usa a coluna):
--   ALTER TABLE public.posts DROP COLUMN IF EXISTS tiktok_options;
--   DELETE FROM migrations WHERE name = '104_posts_tiktok_options.sql';
BEGIN;
SET LOCAL lock_timeout = '10s';

ALTER TABLE public.posts
  ADD COLUMN IF NOT EXISTS tiktok_options jsonb
    CHECK (tiktok_options IS NULL OR jsonb_typeof(tiktok_options) = 'object');

COMMIT;

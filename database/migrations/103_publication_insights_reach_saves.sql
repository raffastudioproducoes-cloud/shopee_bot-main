-- 14/11/2026: Fase 2 de métricas por postagem (Instagram e Facebook).
-- Duas colunas aditivas e anuláveis no cache publication_insights para alcance e
-- salvamentos, que Instagram/Facebook fornecem e Threads não. NULL = a rede não
-- forneceu (nunca 0). Idempotente; o código anterior (3.22.0) lê e grava colunas
-- explícitas, então ignora as novas. RLS e grants da tabela (migração 088) seguem iguais.
--
-- Reversão (somente depois de voltar o código que usa as colunas):
--   ALTER TABLE public.publication_insights DROP COLUMN IF EXISTS reach, DROP COLUMN IF EXISTS saves;
--   DELETE FROM migrations WHERE name = '103_publication_insights_reach_saves.sql';
BEGIN;
SET LOCAL lock_timeout = '10s';

ALTER TABLE public.publication_insights
  ADD COLUMN IF NOT EXISTS reach bigint CHECK (reach IS NULL OR reach >= 0),
  ADD COLUMN IF NOT EXISTS saves bigint CHECK (saves IS NULL OR saves >= 0);

ALTER TABLE public.publication_insights ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.publication_insights FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.publication_insights TO service_role;

COMMIT;

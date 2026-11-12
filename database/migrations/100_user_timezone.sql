-- 12/11/2026: fuso horario por usuario e por agenda. Aditiva e idempotente.
-- Banco compartilhado staging/producao: so colunas novas com DEFAULT; o codigo
-- da main (3.17.0) nao as le nem as escreve e continua funcionando igual.
-- schedulers.run_date (TIMESTAMP sem fuso, horario de Brasilia) nao muda.
-- O nome IANA e validado na API (zoneinfo); aqui so um teto de tamanho.
--
-- Reversao (somente depois de voltar o codigo que le as colunas):
--   ALTER TABLE public.schedulers DROP COLUMN IF EXISTS timezone;
--   ALTER TABLE public.users DROP COLUMN IF EXISTS timezone_updated_at;
--   ALTER TABLE public.users DROP COLUMN IF EXISTS timezone;
--   DELETE FROM migrations WHERE name = '100_user_timezone.sql';
BEGIN;
SET LOCAL lock_timeout = '10s';

-- DEFAULT constante: PostgreSQL 11+ adiciona a coluna sem reescrever a tabela.
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS timezone text NOT NULL DEFAULT 'America/Sao_Paulo';
-- NULL = o usuario nunca confirmou um fuso; o site adota o do dispositivo uma vez.
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS timezone_updated_at timestamptz;
ALTER TABLE public.schedulers
  ADD COLUMN IF NOT EXISTS timezone text NOT NULL DEFAULT 'America/Sao_Paulo';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_timezone_length') THEN
    ALTER TABLE public.users ADD CONSTRAINT users_timezone_length
      CHECK (char_length(timezone) BETWEEN 1 AND 64);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schedulers_timezone_length') THEN
    ALTER TABLE public.schedulers ADD CONSTRAINT schedulers_timezone_length
      CHECK (char_length(timezone) BETWEEN 1 AND 64);
  END IF;
END $$;

COMMIT;

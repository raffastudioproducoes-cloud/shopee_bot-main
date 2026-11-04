-- 084: impedir recriação de logs vinculados após exclusão de conta.
-- NOT VALID preserva registros legados órfãos sem limpeza destrutiva.
-- FK já é aplicada a novas inserções e futuras exclusões.
BEGIN;
SET LOCAL lock_timeout='5s';

CREATE INDEX IF NOT EXISTS idx_request_logs_user_id_fk
  ON public.request_logs(user_id)
  WHERE user_id IS NOT NULL;

DO $guard$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='request_logs_user_id_erasure_fk'
      AND conrelid='public.request_logs'::regclass
  ) THEN
    ALTER TABLE public.request_logs
      ADD CONSTRAINT request_logs_user_id_erasure_fk
      FOREIGN KEY (user_id) REFERENCES public.users(id)
      ON DELETE CASCADE NOT VALID;
  END IF;
END $guard$;

COMMIT;

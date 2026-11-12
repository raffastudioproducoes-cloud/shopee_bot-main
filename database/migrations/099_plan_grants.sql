-- 12/11/2026: concessao de plano pelo ADMIN (Pro/Premium por prazo). Aditiva e idempotente.
-- Banco compartilhado staging/producao: so tabela nova, nada lido pelo codigo main vigente.
-- Navegador nunca le esta tabela: RLS bloqueia tudo, apenas service_role.
BEGIN;
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.plan_grants (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tier text NOT NULL CHECK (tier IN ('pro','premium')),
  previous_tier text,
  granted_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
  granted_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','revoked','superseded')),
  ended_at timestamptz,
  ended_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
  reason text CHECK (reason IS NULL OR char_length(reason) <= 200),
  CONSTRAINT plan_grants_expires_after_grant CHECK (expires_at > granted_at)
);

-- No maximo uma concessao ativa por conta; a varredura de expiracao usa o indice parcial.
CREATE UNIQUE INDEX IF NOT EXISTS plan_grants_one_active_per_user
  ON public.plan_grants (user_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_plan_grants_active_expiry
  ON public.plan_grants (expires_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_plan_grants_user_history
  ON public.plan_grants (user_id, granted_at DESC);

ALTER TABLE public.plan_grants ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.plan_grants FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.plan_grants TO service_role;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='plan_grants'
                 AND policyname='block_all_api') THEN
    CREATE POLICY block_all_api ON public.plan_grants FOR ALL USING (false) WITH CHECK (false);
  END IF;
END $$;

COMMIT;

-- 066: vínculo de identidade Supabase Auth sem alterar os IDs legados.
-- Esta migração é somente ADITIVA: as duas contas antigas continuam em public.users.
-- Executar somente depois de revisar o fluxo OAuth e a configuração de Auth.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS supabase_auth_user_id uuid;
-- Conta criada pelo Supabase Auth não possui senha local. Legados conservam bcrypt.
ALTER TABLE public.users ALTER COLUMN password DROP NOT NULL;

-- Unicidade case-insensitive; NULL é permitido até a vinculação manual dos legados.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower_unique
  ON public.users (lower(email)) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_supabase_auth_user_id_unique
  ON public.users (supabase_auth_user_id)
  WHERE supabase_auth_user_id IS NOT NULL;

-- Um vínculo removido no provedor não deve excluir automaticamente dados comerciais.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.users'::regclass
      AND conname = 'users_supabase_auth_user_id_fkey'
  ) THEN
    ALTER TABLE public.users
      ADD CONSTRAINT users_supabase_auth_user_id_fkey
      FOREIGN KEY (supabase_auth_user_id) REFERENCES auth.users(id)
      ON DELETE SET NULL;
  END IF;
END;
$$;

-- Nenhuma policy nem GRANT novo: a aplicação continua usando acesso privilegiado
-- SOMENTE no servidor e autorização por public.users.id + profile_id.

-- Cadastro e-mail ainda não confirmado: nenhum usuário comercial é criado
-- até que o Supabase confirme a caixa e o primeiro login seja bem-sucedido.
CREATE TABLE IF NOT EXISTS public.pending_auth_registrations (
  auth_user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL,
  username text NOT NULL,
  legal_terms_version text NOT NULL,
  legal_terms_accepted_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_auth_registrations_username_lower
  ON public.pending_auth_registrations (lower(username));
ALTER TABLE public.pending_auth_registrations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.pending_auth_registrations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.pending_auth_registrations TO service_role;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'pending_auth_registrations'
      AND policyname = 'block_all_api'
  ) THEN
    CREATE POLICY block_all_api ON public.pending_auth_registrations
      AS PERMISSIVE FOR ALL TO anon, authenticated
      USING (false) WITH CHECK (false);
  END IF;
END;
$$;

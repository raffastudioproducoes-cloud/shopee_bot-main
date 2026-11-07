-- 07/11/2026: dados cadastrais por CONTA, não por perfil de publicação.
-- Migração aditiva para o Supabase compartilhado; main 3.4.0 continua compatível.
-- Documento CPF guardado cifrado pelo backend; fingerprint HMAC não reversível.

CREATE TABLE IF NOT EXISTS public.account_billing_identity (
  user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
  full_name text,
  cpf_ciphertext text,
  cpf_fingerprint text UNIQUE,
  age smallint CHECK (age BETWEEN 0 AND 120),
  mobile_phone text,
  recovery_email text,
  contact_phone text,
  address_line text,
  address_number text,
  address_complement text,
  neighborhood text,
  city text,
  state text,
  cep text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.account_billing_identity ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.account_billing_identity FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.account_billing_identity TO service_role;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
                 AND tablename='account_billing_identity' AND policyname='block_all_api') THEN
    CREATE POLICY block_all_api ON public.account_billing_identity
      FOR ALL USING (false) WITH CHECK (false);
  END IF;
END $$;

-- Antes da confirmação de e-mail, os dados pessoais ficam pendentes e cifrados.
ALTER TABLE public.pending_auth_registrations ADD COLUMN IF NOT EXISTS full_name text;
ALTER TABLE public.pending_auth_registrations ADD COLUMN IF NOT EXISTS cpf_ciphertext text;
ALTER TABLE public.pending_auth_registrations ADD COLUMN IF NOT EXISTS cpf_fingerprint text;

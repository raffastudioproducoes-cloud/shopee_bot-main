-- 07/11/2026: data de nascimento opcional do titular, preservando idade legada.
-- Expansão aditiva e compatível com main 3.4.0; sem alterar RLS ou grants.
ALTER TABLE public.account_billing_identity
  ADD COLUMN IF NOT EXISTS birth_date date;

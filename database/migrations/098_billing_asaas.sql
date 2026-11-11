-- 10/11/2026: base da cobrança com Asaas (fase 1). Aditiva e idempotente.
-- Banco compartilhado staging/produção: só tabelas novas, nada lido pela main 3.15.0.
-- Navegador nunca lê estas tabelas: RLS bloqueia tudo, apenas service_role.
BEGIN;
SET LOCAL lock_timeout = '10s';

-- Preço mensal por plano pago (centavos), editável pelo ADMIN.
CREATE TABLE IF NOT EXISTS public.plan_prices (
  tier text PRIMARY KEY CHECK (tier IN ('pro','premium')),
  monthly_price_cents integer NOT NULL CHECK (monthly_price_cents > 0),
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.plan_prices (tier, monthly_price_cents) VALUES
  ('pro', 5990), ('premium', 10990)
ON CONFLICT (tier) DO NOTHING;

-- Períodos de contratação e desconto (pontos-base: 250 = 2,5%).
CREATE TABLE IF NOT EXISTS public.plan_periods (
  period text PRIMARY KEY CHECK (period IN ('monthly','quarterly','semiannual','yearly')),
  months smallint NOT NULL CHECK (months IN (1,3,6,12)),
  asaas_cycle text NOT NULL CHECK (asaas_cycle IN ('MONTHLY','QUARTERLY','SEMIANNUALLY','YEARLY')),
  discount_bps integer NOT NULL CHECK (discount_bps BETWEEN 0 AND 5000),
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.plan_periods (period, months, asaas_cycle, discount_bps) VALUES
  ('monthly', 1, 'MONTHLY', 0),
  ('quarterly', 3, 'QUARTERLY', 250),
  ('semiannual', 6, 'SEMIANNUALLY', 500),
  ('yearly', 12, 'YEARLY', 1500)
ON CONFLICT (period) DO NOTHING;

-- Auditoria de mudança de preço/desconto.
CREATE TABLE IF NOT EXISTS public.plan_pricing_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  table_name text NOT NULL,
  row_key text NOT NULL,
  old_row jsonb NOT NULL,
  new_row jsonb NOT NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  changed_by_db_role text NOT NULL DEFAULT current_user
);
CREATE OR REPLACE FUNCTION public.audit_plan_pricing_changes()
RETURNS trigger LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
BEGIN
  NEW.updated_at := now();
  INSERT INTO public.plan_pricing_audit(table_name, row_key, old_row, new_row)
  VALUES (TG_TABLE_NAME, COALESCE(to_jsonb(OLD)->>'tier', to_jsonb(OLD)->>'period'),
          to_jsonb(OLD), to_jsonb(NEW));
  RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS trg_plan_prices_audit ON public.plan_prices;
CREATE TRIGGER trg_plan_prices_audit BEFORE UPDATE ON public.plan_prices
  FOR EACH ROW EXECUTE FUNCTION public.audit_plan_pricing_changes();
DROP TRIGGER IF EXISTS trg_plan_periods_audit ON public.plan_periods;
CREATE TRIGGER trg_plan_periods_audit BEFORE UPDATE ON public.plan_periods
  FOR EACH ROW EXECUTE FUNCTION public.audit_plan_pricing_changes();

-- Conta ↔ cliente no Asaas (um por ambiente: sandbox e produção têm ids diferentes).
CREATE TABLE IF NOT EXISTS public.billing_customers (
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  environment text NOT NULL CHECK (environment IN ('sandbox','production')),
  asaas_customer_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, environment),
  UNIQUE (environment, asaas_customer_id)
);

-- Pedido interno de contratação (externalReference no Asaas).
CREATE TABLE IF NOT EXISTS public.billing_checkouts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  environment text NOT NULL CHECK (environment IN ('sandbox','production')),
  tier text NOT NULL CHECK (tier IN ('pro','premium')),
  period text NOT NULL REFERENCES public.plan_periods(period),
  billing_type text NOT NULL CHECK (billing_type IN ('CREDIT_CARD','PIX')),
  value_cents integer NOT NULL CHECK (value_cents > 0),
  asaas_checkout_id text UNIQUE,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','active','paid','canceled','expired','failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_billing_checkouts_user ON public.billing_checkouts (user_id, created_at DESC);

-- Assinatura vigente por conta.
CREATE TABLE IF NOT EXISTS public.billing_subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  environment text NOT NULL CHECK (environment IN ('sandbox','production')),
  asaas_subscription_id text NOT NULL,
  tier text NOT NULL CHECK (tier IN ('pro','premium')),
  period text NOT NULL REFERENCES public.plan_periods(period),
  billing_type text NOT NULL CHECK (billing_type IN ('CREDIT_CARD','PIX')),
  value_cents integer NOT NULL CHECK (value_cents > 0),
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','active','overdue','canceled','inactive')),
  current_period_end date,
  overdue_since date,
  scheduled_change jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (environment, asaas_subscription_id)
);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_user ON public.billing_subscriptions (user_id, created_at DESC);

-- Histórico de cobranças geradas pelo Asaas.
CREATE TABLE IF NOT EXISTS public.billing_payments (
  environment text NOT NULL CHECK (environment IN ('sandbox','production')),
  asaas_payment_id text NOT NULL,
  user_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
  asaas_subscription_id text,
  billing_type text,
  status text NOT NULL,
  value_cents integer,
  due_date date,
  paid_at timestamptz,
  invoice_url text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (environment, asaas_payment_id)
);
CREATE INDEX IF NOT EXISTS idx_billing_payments_user ON public.billing_payments (user_id, due_date DESC);

-- Eventos de webhook: entrega "at least once"; o id do evento é a chave de idempotência.
CREATE TABLE IF NOT EXISTS public.billing_webhook_events (
  environment text NOT NULL CHECK (environment IN ('sandbox','production')),
  event_id text NOT NULL,
  event_type text NOT NULL,
  payload jsonb NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  attempts integer NOT NULL DEFAULT 0,
  last_error text,
  PRIMARY KEY (environment, event_id)
);
CREATE INDEX IF NOT EXISTS idx_billing_webhook_pending
  ON public.billing_webhook_events (received_at) WHERE processed_at IS NULL;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['plan_prices','plan_periods','plan_pricing_audit','billing_customers',
                           'billing_checkouts','billing_subscriptions','billing_payments',
                           'billing_webhook_events'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', t);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO service_role', t);
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=t
                   AND policyname='block_all_api') THEN
      EXECUTE format('CREATE POLICY block_all_api ON public.%I FOR ALL USING (false) WITH CHECK (false)', t);
    END IF;
  END LOOP;
END $$;
REVOKE ALL ON FUNCTION public.audit_plan_pricing_changes() FROM PUBLIC, anon, authenticated;

COMMIT;

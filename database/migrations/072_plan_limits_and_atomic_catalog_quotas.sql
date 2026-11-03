-- F4B: catálogo de cotas comerciais persistente e inserções atômicas opt-in.
-- Banco compartilhado: produção anterior continua usando INSERT normal.
-- A API staging chama RPC; nunca instalar trigger global de produtos/listas nesta fase.
BEGIN;
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.plan_limits (
  tier text PRIMARY KEY CHECK (tier IN ('free','pro','premium')),
  products_per_account integer NOT NULL CHECK (products_per_account >= 0),
  lists_per_profile integer NOT NULL CHECK (lists_per_profile >= 0),
  immediate_per_hour integer NOT NULL CHECK (immediate_per_hour >= 0),
  recurring_slots_per_day integer NOT NULL CHECK (recurring_slots_per_day >= 0),
  active_campaigns_per_profile integer NOT NULL CHECK (active_campaigns_per_profile >= 0),
  campaign_days integer NOT NULL CHECK (campaign_days >= 0),
  campaign_posts_per_day integer NOT NULL CHECK (campaign_posts_per_day >= 0),
  max_profiles_per_account integer NOT NULL CHECK (max_profiles_per_account >= 1),
  automation_enabled boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.plan_limits
  (tier,products_per_account,lists_per_profile,immediate_per_hour,
   recurring_slots_per_day,active_campaigns_per_profile,campaign_days,
   campaign_posts_per_day,max_profiles_per_account,automation_enabled)
VALUES
  ('free',100,20,1,1,0,0,0,1,false),
  ('pro',500,20,3,5,2,15,3,3,false),
  ('premium',2000,100,5,5,5,30,15,3,true)
ON CONFLICT (tier) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.plan_limits_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tier text NOT NULL,
  old_policy jsonb NOT NULL,
  new_policy jsonb NOT NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  changed_by_db_role text NOT NULL DEFAULT current_user
);
CREATE OR REPLACE FUNCTION public.audit_plan_limits_changes()
RETURNS trigger LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
BEGIN
  NEW.updated_at := now();
  INSERT INTO public.plan_limits_audit(tier,old_policy,new_policy)
  VALUES (OLD.tier,to_jsonb(OLD),to_jsonb(NEW));
  RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS trg_audit_plan_limits_changes ON public.plan_limits;
CREATE TRIGGER trg_audit_plan_limits_changes
  BEFORE UPDATE ON public.plan_limits FOR EACH ROW
  WHEN (OLD IS DISTINCT FROM NEW)
  EXECUTE FUNCTION public.audit_plan_limits_changes();

-- Plano canônico fica na CONTA, não em cada perfil.
-- Backfill somente na primeira criação da coluna (não desfaz downgrade posterior).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='users' AND column_name='plan_tier'
  ) THEN
    ALTER TABLE public.users ADD COLUMN plan_tier text NOT NULL DEFAULT 'free';
    UPDATE public.users u SET plan_tier = CASE
      WHEN p.plan_tier='plus' THEN 'pro' ELSE p.plan_tier END
    FROM public.profiles p
    WHERE p.user_id=u.id AND p.kind='principal'
      AND p.plan_tier IN ('plus','premium');
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.users'::regclass AND conname='users_plan_tier_check'
  ) THEN
    ALTER TABLE public.users ADD CONSTRAINT users_plan_tier_check
      CHECK (plan_tier IN ('free','pro','plus','premium'));
  END IF;
END $$;

-- SERIALIZA inserções da mesma conta com lock de users FOR UPDATE.
-- A credencial de service_role só é usada no servidor; usuários externos
-- não têm EXECUTE. Funções SECURITY INVOKER (sem escalada de papéis).
CREATE OR REPLACE FUNCTION public.insert_product_with_plan_quota(
  p_user_id uuid, p_product jsonb
) RETURNS SETOF public.products
LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp AS $$
DECLARE
  v_access text;
  v_tier text;
  v_max integer;
BEGIN
  SELECT access::text, CASE WHEN plan_tier='plus' THEN 'pro' ELSE plan_tier END
    INTO v_access,v_tier FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001'; END IF;
  IF v_access <> 'ADMIN' THEN
    SELECT products_per_account INTO v_max FROM public.plan_limits WHERE tier=v_tier;
    IF v_max IS NULL THEN RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001'; END IF;
    IF (SELECT count(*) FROM public.products WHERE user_id=p_user_id) >= v_max THEN
      RAISE EXCEPTION 'plan_products_quota_exceeded' USING ERRCODE='P0001';
    END IF;
  END IF;
  RETURN QUERY INSERT INTO public.products
    (user_id,product_id,name,original_link,commission_link,
     commission,image,price_min,price_max)
  VALUES (p_user_id,(p_product->>'product_id')::bigint,p_product->>'name',
     p_product->>'original_link',p_product->>'commission_link',
     p_product->>'commission',p_product->>'image',
     p_product->>'price_min',p_product->>'price_max')
  RETURNING *;
END; $$;

CREATE OR REPLACE FUNCTION public.insert_product_list_with_plan_quota(
  p_user_id uuid, p_profile_id uuid, p_name text
) RETURNS SETOF public.product_lists
LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp AS $$
DECLARE
  v_access text;
  v_tier text;
  v_max integer;
BEGIN
  SELECT access::text,CASE WHEN plan_tier='plus' THEN 'pro' ELSE plan_tier END
    INTO v_access,v_tier FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001'; END IF;
  IF NOT EXISTS(SELECT 1 FROM public.profiles WHERE id=p_profile_id AND user_id=p_user_id) THEN
    RAISE EXCEPTION 'profile_not_owned' USING ERRCODE='P0001';
  END IF;
  IF v_access <> 'ADMIN' THEN
    SELECT lists_per_profile INTO v_max FROM public.plan_limits WHERE tier=v_tier;
    IF v_max IS NULL THEN RAISE EXCEPTION 'plan_policy_unavailable' USING ERRCODE='P0001'; END IF;
    IF (SELECT count(*) FROM public.product_lists
        WHERE user_id=p_user_id AND profile_id=p_profile_id) >= v_max THEN
      RAISE EXCEPTION 'plan_lists_quota_exceeded' USING ERRCODE='P0001';
    END IF;
  END IF;
  RETURN QUERY INSERT INTO public.product_lists (user_id,profile_id,name)
  VALUES(p_user_id,p_profile_id,p_name) RETURNING *;
END; $$;

ALTER TABLE public.plan_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plan_limits_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.plan_limits, public.plan_limits_audit FROM anon,authenticated;
REVOKE ALL ON SEQUENCE public.plan_limits_audit_id_seq FROM anon,authenticated;
REVOKE ALL ON FUNCTION public.audit_plan_limits_changes() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.insert_product_with_plan_quota(uuid,jsonb) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.insert_product_list_with_plan_quota(uuid,uuid,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.insert_product_with_plan_quota(uuid,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.insert_product_list_with_plan_quota(uuid,uuid,text) TO service_role;
COMMIT;
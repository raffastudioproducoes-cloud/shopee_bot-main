-- F3A: rascunhos de campanha inertes. Não cria posts, schedulers ou jobs.
-- Banco compartilhado staging/produção: aplicar SOMENTE após aprovação
-- específica e revisão de migrations existentes. Esta migration não roda no deploy.
BEGIN;
SET LOCAL lock_timeout = '10s';

CREATE TABLE IF NOT EXISTS public.campaign_drafts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    source_list_id integer REFERENCES public.product_lists(id) ON DELETE SET NULL,
    source_list_name text NOT NULL,
    items jsonb NOT NULL,
    schedule jsonb,
    status text NOT NULL DEFAULT 'draft' CHECK (status = 'draft'),
    revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT campaign_drafts_name_size CHECK (char_length(source_list_name) BETWEEN 1 AND 300),
    CONSTRAINT campaign_drafts_items_shape CHECK (
      jsonb_typeof(items) = 'array'
      AND jsonb_array_length(items) BETWEEN 1 AND 100
      AND octet_length(items::text) <= 1048576
    ),
    CONSTRAINT campaign_drafts_schedule_shape CHECK (
      schedule IS NULL OR jsonb_typeof(schedule) = 'object'
    )
);

CREATE INDEX IF NOT EXISTS idx_campaign_drafts_owner_updated
  ON public.campaign_drafts (user_id, profile_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaign_drafts_source_list_fk
  ON public.campaign_drafts (source_list_id);

-- Segurança em profundidade: mesma conta/perfil e lista-fonte em INSERT/UPDATE.
-- O campo source_list_id pode ficar NULL após a exclusão da lista-fonte;
-- o snapshot independente continua utilizável.
CREATE OR REPLACE FUNCTION public.check_campaign_draft_ownership()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.profiles p
    WHERE p.id = NEW.profile_id AND p.user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'INVALID_CAMPAIGN_PROFILE' USING ERRCODE = '23514';
  END IF;
  IF NEW.source_list_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.product_lists l
    WHERE l.id = NEW.source_list_id
      AND l.user_id = NEW.user_id
      AND l.profile_id = NEW.profile_id
  ) THEN
    RAISE EXCEPTION 'INVALID_CAMPAIGN_LIST' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;
-- A aplicação também executa migrations no boot; o Supabase já pode ter
-- recebido esta DDL pelo MCP. Instalar o trigger só se ainda não existe.
DO $campaign_trigger$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_trigger
    WHERE tgrelid = 'public.campaign_drafts'::regclass
      AND tgname = 'trg_campaign_draft_owner'
      AND NOT tgisinternal
  ) THEN
    CREATE TRIGGER trg_campaign_draft_owner
    BEFORE INSERT OR UPDATE ON public.campaign_drafts
    FOR EACH ROW EXECUTE FUNCTION public.check_campaign_draft_ownership();
  END IF;
END
$campaign_trigger$;

ALTER TABLE public.campaign_drafts ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.campaign_drafts FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_drafts TO service_role;
REVOKE ALL ON FUNCTION public.check_campaign_draft_ownership() FROM PUBLIC, anon, authenticated;

COMMIT;

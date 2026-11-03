-- F3B: nome próprio da campanha e anexos duráveis por produto.
-- Banco compartilhado staging/produção: NÃO aplicar sem aprovação específica.
-- O migrador da aplicação pode executar este arquivo novamente durante o boot.
BEGIN;
SET LOCAL lock_timeout = '10s';

ALTER TABLE public.campaign_drafts
  ADD COLUMN IF NOT EXISTS campaign_name text;
UPDATE public.campaign_drafts
  SET campaign_name = LEFT(BTRIM(source_list_name), 120)
  WHERE campaign_name IS NULL OR BTRIM(campaign_name) = '';
ALTER TABLE public.campaign_drafts
  ALTER COLUMN campaign_name SET NOT NULL;
DO $campaign_name_constraint$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint
      WHERE conrelid = 'public.campaign_drafts'::regclass
        AND conname = 'campaign_drafts_campaign_name_size') THEN
    ALTER TABLE public.campaign_drafts ADD CONSTRAINT campaign_drafts_campaign_name_size
      CHECK (char_length(BTRIM(campaign_name)) BETWEEN 1 AND 120);
  END IF;
END
$campaign_name_constraint$;

-- Proteger imagens/vídeos da limpeza de 24h dos uploads temporários.
-- Bucket privado post-media já existe; arquivos ficam no prefixo campaigns/.
CREATE TABLE IF NOT EXISTS public.campaign_draft_media (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id uuid NOT NULL REFERENCES public.campaign_drafts(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  product_id integer NOT NULL CHECK (product_id > 0),
  slot smallint NOT NULL CHECK (slot BETWEEN 0 AND 9),
  storage_bucket text NOT NULL DEFAULT 'post-media' CHECK (storage_bucket = 'post-media'),
  storage_key text NOT NULL UNIQUE,
  file_name text NOT NULL CHECK (char_length(file_name) BETWEEN 1 AND 255),
  mime_type text NOT NULL,
  media_type text NOT NULL CHECK (media_type IN ('IMAGE', 'VIDEO')),
  size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 52428800),
  status text NOT NULL DEFAULT 'uploading'
    CHECK (status IN ('uploading', 'ready', 'delete_failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (campaign_id, product_id, slot)
);
CREATE INDEX IF NOT EXISTS idx_campaign_draft_media_owner
  ON public.campaign_draft_media (user_id, profile_id, campaign_id, product_id);

CREATE OR REPLACE FUNCTION public.check_campaign_media_owner()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.campaign_drafts c
    WHERE c.id = NEW.campaign_id AND c.user_id = NEW.user_id
      AND c.profile_id = NEW.profile_id AND c.status = 'draft'
      AND EXISTS (
        SELECT 1 FROM jsonb_array_elements(c.items) AS entry
        WHERE (entry->>'product_id')::integer = NEW.product_id
      )
  ) THEN
    RAISE EXCEPTION 'INVALID_CAMPAIGN_MEDIA_OWNER_OR_PRODUCT'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;

DO $campaign_media_trigger$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_trigger
    WHERE tgrelid = 'public.campaign_draft_media'::regclass
      AND tgname = 'trg_campaign_media_owner'
      AND NOT tgisinternal
  ) THEN
    CREATE TRIGGER trg_campaign_media_owner
      BEFORE INSERT OR UPDATE ON public.campaign_draft_media
      FOR EACH ROW EXECUTE FUNCTION public.check_campaign_media_owner();
  END IF;
END
$campaign_media_trigger$;

ALTER TABLE public.campaign_draft_media ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.campaign_draft_media FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_draft_media TO service_role;
REVOKE ALL ON FUNCTION public.check_campaign_media_owner() FROM PUBLIC, anon, authenticated;

COMMIT;

-- Produto: cópia curta e galeria privada permanente.
-- Aditiva e compatível com main; Supabase único para staging e produção.
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS description text;
ALTER TABLE public.products
  ADD CONSTRAINT products_description_short_no_url
  CHECK (description IS NULL OR (char_length(description) <= 280
    AND description !~* '(https?://|www[.]|shopee[.]com|s[.]shopee)')) NOT VALID;

CREATE TABLE IF NOT EXISTS public.product_media (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  product_id integer NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  media_type text NOT NULL CHECK (media_type IN ('IMAGE', 'VIDEO')),
  slot smallint NOT NULL,
  file_name text NOT NULL,
  mime_type text NOT NULL,
  size_bytes integer NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 52428800),
  storage_key text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'uploading' CHECK (status IN ('uploading', 'ready')),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT product_media_slots CHECK (
    (media_type = 'IMAGE' AND slot BETWEEN 1 AND 5) OR
    (media_type = 'VIDEO' AND slot BETWEEN 1 AND 2)),
  CONSTRAINT product_media_one_asset_per_slot UNIQUE (product_id, media_type, slot)
);
CREATE INDEX IF NOT EXISTS idx_product_media_owner ON public.product_media(user_id, product_id);
ALTER TABLE public.product_media ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.product_media FROM anon, authenticated;
COMMENT ON TABLE public.product_media IS 'Galeria privada do produto: 5 imagens + 2 vídeos, objetos no bucket post-media.';

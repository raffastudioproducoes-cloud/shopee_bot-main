-- 060: explicit registration terms acceptance and revocable GPS preference.
-- No latitude, longitude, IP or device identifier is stored by this migration.
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS legal_terms_version text,
  ADD COLUMN IF NOT EXISTS legal_terms_accepted_at timestamptz,
  ADD COLUMN IF NOT EXISTS gps_consent_version text,
  ADD COLUMN IF NOT EXISTS gps_consented_at timestamptz;
COMMENT ON COLUMN public.users.legal_terms_version IS 'Version of mandatory service terms acknowledged upon signup; not consent for optional processing.';
COMMENT ON COLUMN public.users.gps_consented_at IS 'Optional GPS preference, not evidence of browser permission; revoked by setting NULL.';
COMMENT ON COLUMN public.users.gps_consent_version IS 'Version of location purpose notice; coordinates are never saved.';

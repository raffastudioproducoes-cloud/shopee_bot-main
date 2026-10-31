-- 061: explicit, revocable, one-time location sharing for growth analysis.
-- Browser rounds position to ~1 km BEFORE transmission; no address, IP or movement history.
-- A declined/revoked tombstone prevents prompting or collecting again after a decision.
CREATE TABLE IF NOT EXISTS public.account_location_sharing (
  user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
  choice text NOT NULL CHECK (choice IN ('accepted','declined','revoked')),
  latitude numeric(5,2),
  longitude numeric(5,2),
  accuracy_m integer CHECK (accuracy_m IS NULL OR accuracy_m BETWEEN 0 AND 1000000),
  consent_version text NOT NULL,
  decided_at timestamptz NOT NULL DEFAULT now(),
  collected_at timestamptz,
  CONSTRAINT valid_location_sharing CHECK (
    (choice IN ('declined','revoked') AND latitude IS NULL AND longitude IS NULL AND accuracy_m IS NULL AND collected_at IS NULL)
    OR (choice='accepted' AND latitude IS NOT NULL AND longitude IS NOT NULL AND collected_at IS NOT NULL)
  ),
  CONSTRAINT lat_range CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CONSTRAINT lon_range CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);
ALTER TABLE public.account_location_sharing ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.account_location_sharing FROM PUBLIC, anon, authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE public.account_location_sharing TO service_role;
COMMENT ON TABLE public.account_location_sharing IS 'Opt-in approximate GPS-derived location; one current location per account; delete point on revocation; admin-only analysis.';

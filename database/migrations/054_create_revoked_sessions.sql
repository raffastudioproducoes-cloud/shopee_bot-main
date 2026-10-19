-- Revogacao por identificador assinado, nunca pelo texto bruto do JWT.
CREATE TABLE IF NOT EXISTS public.revoked_sessions (
    jti UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS revoked_sessions_expires_at_idx
    ON public.revoked_sessions (expires_at);

ALTER TABLE public.revoked_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.revoked_sessions FROM anon, authenticated;

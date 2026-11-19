-- Keep verification and password-reset token tables backend-only.
-- This column is part of the email-verification workflow; add it safely when
-- upgrading databases that previously relied on runtime metadata creation.
ALTER TABLE public.user_accounts ADD COLUMN IF NOT EXISTS email_verified_at varchar(40);

-- TutorInn's browser uses FastAPI/JWT and must not access these tables through
-- the Supabase Data API. RLS is enabled with no browser policies by design.
ALTER TABLE public.email_verification_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.password_reset_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE
  public.email_verification_tokens,
  public.password_reset_requests,
  public.password_reset_tokens
FROM PUBLIC;

REVOKE ALL PRIVILEGES ON SEQUENCE
  public.email_verification_tokens_id_seq,
  public.password_reset_requests_id_seq,
  public.password_reset_tokens_id_seq
FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.email_verification_tokens, public.password_reset_requests, public.password_reset_tokens FROM anon';
    EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE public.email_verification_tokens_id_seq, public.password_reset_requests_id_seq, public.password_reset_tokens_id_seq FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.email_verification_tokens, public.password_reset_requests, public.password_reset_tokens FROM authenticated';
    EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE public.email_verification_tokens_id_seq, public.password_reset_requests_id_seq, public.password_reset_tokens_id_seq FROM authenticated';
  END IF;
END
$$;

-- Pin the trigger function's resolution path to trusted schemas.
ALTER FUNCTION public.tutorinn_protect_first_admin()
  SET search_path = pg_catalog, public;

-- Keep account-deletion and former-user privacy records backend-only.
-- Browser roles have neither direct table grants nor RLS policies.
ALTER TABLE public.account_deletion_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.retained_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.former_user_content_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.former_user_content_removal_requests ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE
  public.account_deletion_requests,
  public.retained_content,
  public.former_user_content_tokens,
  public.former_user_content_removal_requests
FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.account_deletion_requests, public.retained_content, public.former_user_content_tokens, public.former_user_content_removal_requests FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.account_deletion_requests, public.retained_content, public.former_user_content_tokens, public.former_user_content_removal_requests FROM authenticated';
  END IF;
END
$$;

-- Supabase service_role retains its existing BYPASSRLS privileges.

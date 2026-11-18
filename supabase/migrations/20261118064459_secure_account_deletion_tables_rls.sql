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
FROM PUBLIC, anon, authenticated;

-- The FastAPI backend connects with the trusted PostgreSQL/service role.
-- Preserve service_role privileges; it has BYPASSRLS in Supabase.

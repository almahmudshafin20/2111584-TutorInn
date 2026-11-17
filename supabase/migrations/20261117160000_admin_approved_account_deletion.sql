-- Admin-approved account deletion requests. Keep only a non-identifying review record after approval.
CREATE TABLE IF NOT EXISTS public.account_deletion_requests (
  id SERIAL PRIMARY KEY, account_id INTEGER NULL, account_email VARCHAR(255) NOT NULL,
  account_role VARCHAR(16) NOT NULL CHECK (account_role IN ('student', 'tutor')),
  reason VARCHAR(500) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  requested_at VARCHAR(40) NOT NULL, reviewed_at VARCHAR(40) NULL,
  reviewed_by_account_id INTEGER NULL REFERENCES public.user_accounts(id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_account_deletion_pending ON public.account_deletion_requests(account_id) WHERE status = 'pending' AND account_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_account_deletion_requests_status ON public.account_deletion_requests(status);
CREATE INDEX IF NOT EXISTS ix_account_deletion_requests_account_id ON public.account_deletion_requests(account_id);
ALTER TABLE public.account_deletion_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.account_deletion_requests FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON SEQUENCE public.account_deletion_requests_id_seq FROM PUBLIC, anon, authenticated;
GRANT ALL PRIVILEGES ON TABLE public.account_deletion_requests TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.account_deletion_requests_id_seq TO service_role;

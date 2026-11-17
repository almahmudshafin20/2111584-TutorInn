-- Persist former-user link delivery state and prevent concurrent pending removal requests.
ALTER TABLE public.account_deletion_requests
  ADD COLUMN IF NOT EXISTS former_user_link_status VARCHAR(20) NOT NULL DEFAULT 'not_sent';

CREATE UNIQUE INDEX IF NOT EXISTS uq_former_user_removal_pending
  ON public.former_user_content_removal_requests(deletion_request_id)
  WHERE status = 'pending';

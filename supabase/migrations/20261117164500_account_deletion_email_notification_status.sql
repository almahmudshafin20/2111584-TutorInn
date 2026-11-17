-- Record whether the Admin's final account-deletion decision was emailed.
ALTER TABLE public.account_deletion_requests
  ADD COLUMN IF NOT EXISTS notification_status VARCHAR(20) NOT NULL DEFAULT 'not_sent';
ALTER TABLE public.account_deletion_requests
  ADD CONSTRAINT account_deletion_notification_status_check
  CHECK (notification_status IN ('not_sent', 'sent', 'not_configured', 'failed'));

-- Add user preference and Admin-final deletion method to deletion receipts.
ALTER TABLE public.account_deletion_requests
  ADD COLUMN IF NOT EXISTS requested_option VARCHAR(16) NOT NULL DEFAULT 'complete',
  ADD COLUMN IF NOT EXISTS final_option VARCHAR(16) NULL;
ALTER TABLE public.account_deletion_requests
  ADD CONSTRAINT account_deletion_requested_option_check CHECK (requested_option IN ('anonymize', 'complete')),
  ADD CONSTRAINT account_deletion_final_option_check CHECK (final_option IS NULL OR final_option IN ('anonymize', 'complete'));

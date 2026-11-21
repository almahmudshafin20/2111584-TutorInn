-- Retire the legacy profile claim-code workflow.
-- Keep the earlier additive migration in history; this forward migration removes
-- the now-unused credential columns without touching existing Student/Tutor data.
ALTER TABLE IF EXISTS public.students
  DROP COLUMN IF EXISTS claim_token_hash,
  DROP COLUMN IF EXISTS claim_expires_at;

ALTER TABLE IF EXISTS public.tutors
  DROP COLUMN IF EXISTS claim_token_hash,
  DROP COLUMN IF EXISTS claim_expires_at;

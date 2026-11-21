-- Restore the legacy profile claim-token columns so the repo history matches production.
-- Production still has these nullable columns; an earlier migration dropped them in the
-- repo history only. IF NOT EXISTS makes this a no-op on production and recreates the
-- same nullable columns on a clean database. No existing Student/Tutor data is touched.
ALTER TABLE IF EXISTS public.students
  ADD COLUMN IF NOT EXISTS claim_token_hash VARCHAR(64),
  ADD COLUMN IF NOT EXISTS claim_expires_at VARCHAR(40);

ALTER TABLE IF EXISTS public.tutors
  ADD COLUMN IF NOT EXISTS claim_token_hash VARCHAR(64),
  ADD COLUMN IF NOT EXISTS claim_expires_at VARCHAR(40);

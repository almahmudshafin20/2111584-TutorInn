-- Short-lived one-time claim credentials are stored only as SHA-256 hashes.
-- The Admin issues a code only after verifying legacy profile ownership out of band.
ALTER TABLE public.students
  ADD COLUMN IF NOT EXISTS claim_token_hash VARCHAR(64),
  ADD COLUMN IF NOT EXISTS claim_expires_at VARCHAR(40);

ALTER TABLE public.tutors
  ADD COLUMN IF NOT EXISTS claim_token_hash VARCHAR(64),
  ADD COLUMN IF NOT EXISTS claim_expires_at VARCHAR(40);

-- Keep Data API access denied; claim issuance/consumption is handled by FastAPI.
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tutors ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON public.students, public.tutors FROM PUBLIC, anon, authenticated;

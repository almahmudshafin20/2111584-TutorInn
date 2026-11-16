-- Keep TutorInn's verification metadata accessible only through the trusted FastAPI service.
ALTER TABLE public.tutor_verifications ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.tutor_verifications FROM anon, authenticated, PUBLIC;
REVOKE ALL ON SEQUENCE public.tutor_verifications_id_seq FROM anon, authenticated, PUBLIC;

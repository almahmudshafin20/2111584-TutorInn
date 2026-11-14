-- TutorInn uses its own FastAPI/JWT authentication. Browser clients do not
-- access these tables through the Supabase Data API, so no anon/authenticated
-- row policies are appropriate. Server-side postgres access remains intact.

ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tutors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interest_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.refresh_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.security_events ENABLE ROW LEVEL SECURITY;

-- Remove direct Data API access from public, anon, and authenticated roles.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, anon, authenticated;
REVOKE USAGE ON SCHEMA public FROM PUBLIC, anon, authenticated;

-- Prevent future tables/sequences created by the application postgres role
-- from inheriting broad Data API privileges.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;

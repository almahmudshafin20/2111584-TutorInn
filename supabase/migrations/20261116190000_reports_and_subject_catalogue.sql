-- User-generated moderation reports and the Admin-managed subject catalogue.
-- Browser clients use TutorInn's FastAPI/JWT API, not the Supabase Data API.
CREATE TABLE IF NOT EXISTS public.managed_subjects (
  id serial PRIMARY KEY,
  name varchar(80) NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at varchar(40) NOT NULL,
  updated_at varchar(40) NOT NULL,
  CONSTRAINT uq_managed_subject_name UNIQUE (name)
);

CREATE INDEX IF NOT EXISTS ix_managed_subjects_id
  ON public.managed_subjects (id);
CREATE INDEX IF NOT EXISTS ix_managed_subjects_active
  ON public.managed_subjects (active);

CREATE TABLE IF NOT EXISTS public.content_reports (
  id serial PRIMARY KEY,
  reporter_account_id integer NOT NULL REFERENCES public.user_accounts(id) ON DELETE CASCADE,
  target_type varchar(24) NOT NULL,
  target_role varchar(12),
  target_id integer NOT NULL,
  reason varchar(40) NOT NULL,
  description varchar(2000) NOT NULL DEFAULT '',
  status varchar(20) NOT NULL DEFAULT 'pending',
  review_note varchar(1000) NOT NULL DEFAULT '',
  reviewed_by_account_id integer REFERENCES public.user_accounts(id),
  reviewed_at varchar(40),
  created_at varchar(40) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_content_reports_id
  ON public.content_reports (id);
CREATE INDEX IF NOT EXISTS ix_content_reports_reporter_account_id
  ON public.content_reports (reporter_account_id);
CREATE INDEX IF NOT EXISTS ix_content_reports_status
  ON public.content_reports (status);
CREATE INDEX IF NOT EXISTS ix_content_reports_status_created
  ON public.content_reports (status, created_at);
CREATE INDEX IF NOT EXISTS ix_content_reports_target
  ON public.content_reports (target_type, target_id);
CREATE INDEX IF NOT EXISTS ix_content_reports_reporter_created
  ON public.content_reports (reporter_account_id, created_at);

ALTER TABLE public.managed_subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_reports ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.managed_subjects, public.content_reports
  FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON SEQUENCE public.managed_subjects_id_seq, public.content_reports_id_seq
  FROM PUBLIC, anon, authenticated;

-- Expand deletion choices and support retained-content ownership and former-user follow-up requests.
-- This migration is intentionally committed only to the feature branch; do not apply to shared Supabase yet.
ALTER TABLE public.account_deletion_requests
  ADD COLUMN IF NOT EXISTS former_user_email VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS requested_account_action VARCHAR(24) NOT NULL DEFAULT 'delete_account',
  ADD COLUMN IF NOT EXISTS requested_content_action VARCHAR(24) NOT NULL DEFAULT 'delete_all',
  ADD COLUMN IF NOT EXISTS requested_content_ids TEXT NOT NULL DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS requested_visibility VARCHAR(12) NOT NULL DEFAULT 'visible',
  ADD COLUMN IF NOT EXISTS requested_anonymize_content BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS final_account_action VARCHAR(24) NULL,
  ADD COLUMN IF NOT EXISTS final_content_action VARCHAR(24) NULL,
  ADD COLUMN IF NOT EXISTS final_content_ids TEXT NULL,
  ADD COLUMN IF NOT EXISTS final_visibility VARCHAR(12) NULL,
  ADD COLUMN IF NOT EXISTS final_anonymize_content BOOLEAN NULL;

ALTER TABLE public.account_deletion_requests
  ADD CONSTRAINT account_deletion_requested_account_action_check CHECK (requested_account_action IN ('delete_account')),
  ADD CONSTRAINT account_deletion_requested_content_action_check CHECK (requested_content_action IN ('account_only', 'delete_selected', 'delete_all', 'retain_all')),
  ADD CONSTRAINT account_deletion_requested_visibility_check CHECK (requested_visibility IN ('visible', 'hidden')),
  ADD CONSTRAINT account_deletion_final_account_action_check CHECK (final_account_action IS NULL OR final_account_action IN ('delete_account')),
  ADD CONSTRAINT account_deletion_final_content_action_check CHECK (final_content_action IS NULL OR final_content_action IN ('account_only', 'delete_selected', 'delete_all', 'retain_all')),
  ADD CONSTRAINT account_deletion_final_visibility_check CHECK (final_visibility IS NULL OR final_visibility IN ('visible', 'hidden'));

CREATE TABLE IF NOT EXISTS public.retained_content (
  id BIGSERIAL PRIMARY KEY,
  deletion_request_id INTEGER NOT NULL REFERENCES public.account_deletion_requests(id) ON DELETE CASCADE,
  content_type VARCHAR(32) NOT NULL,
  content_id INTEGER NOT NULL,
  visibility VARCHAR(12) NOT NULL DEFAULT 'visible' CHECK (visibility IN ('visible', 'hidden')),
  anonymized BOOLEAN NOT NULL DEFAULT FALSE,
  created_at VARCHAR(40) NOT NULL,
  CONSTRAINT uq_retained_content_item UNIQUE (deletion_request_id, content_type, content_id)
);
CREATE INDEX IF NOT EXISTS ix_retained_content_owner_request ON public.retained_content(deletion_request_id, visibility);

CREATE TABLE IF NOT EXISTS public.former_user_content_tokens (
  id BIGSERIAL PRIMARY KEY,
  deletion_request_id INTEGER NOT NULL REFERENCES public.account_deletion_requests(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at VARCHAR(40) NOT NULL,
  consumed_at VARCHAR(40) NULL,
  created_at VARCHAR(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_former_user_content_tokens_expiry ON public.former_user_content_tokens(expires_at);

CREATE TABLE IF NOT EXISTS public.former_user_content_removal_requests (
  id BIGSERIAL PRIMARY KEY,
  deletion_request_id INTEGER NOT NULL REFERENCES public.account_deletion_requests(id) ON DELETE CASCADE,
  selected_content TEXT NOT NULL DEFAULT '[]',
  status VARCHAR(16) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  requested_at VARCHAR(40) NOT NULL,
  reviewed_at VARCHAR(40) NULL,
  reviewed_by_account_id INTEGER NULL REFERENCES public.user_accounts(id) ON DELETE SET NULL,
  review_note VARCHAR(1000) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_former_user_content_removal_status ON public.former_user_content_removal_requests(status);

ALTER TABLE public.retained_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.former_user_content_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.former_user_content_removal_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.retained_content, public.former_user_content_tokens, public.former_user_content_removal_requests FROM PUBLIC, anon, authenticated;
GRANT ALL PRIVILEGES ON TABLE public.retained_content, public.former_user_content_tokens, public.former_user_content_removal_requests TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.retained_content_id_seq, public.former_user_content_tokens_id_seq, public.former_user_content_removal_requests_id_seq TO service_role;

-- Retained content must survive removal of its former owner's account.
-- Detach nullable ownership references instead of cascading away user-created work.
ALTER TABLE public.personal_learning_tasks
  ALTER COLUMN owner_account_id DROP NOT NULL;
ALTER TABLE public.personal_learning_tasks
  DROP CONSTRAINT IF EXISTS personal_learning_tasks_owner_account_id_fkey,
  ADD CONSTRAINT personal_learning_tasks_owner_account_id_fkey
    FOREIGN KEY (owner_account_id) REFERENCES public.user_accounts(id) ON DELETE SET NULL;

ALTER TABLE public.learning_groups
  ALTER COLUMN owner_account_id DROP NOT NULL;
ALTER TABLE public.learning_groups
  DROP CONSTRAINT IF EXISTS learning_groups_owner_account_id_fkey,
  ADD CONSTRAINT learning_groups_owner_account_id_fkey
    FOREIGN KEY (owner_account_id) REFERENCES public.user_accounts(id) ON DELETE SET NULL;

ALTER TABLE public.group_learning_tasks
  ALTER COLUMN created_by_account_id DROP NOT NULL;
ALTER TABLE public.group_learning_tasks
  DROP CONSTRAINT IF EXISTS group_learning_tasks_created_by_account_id_fkey,
  ADD CONSTRAINT group_learning_tasks_created_by_account_id_fkey
    FOREIGN KEY (created_by_account_id) REFERENCES public.user_accounts(id) ON DELETE SET NULL;

ALTER TABLE public.learning_group_members
  ALTER COLUMN student_account_id DROP NOT NULL;
ALTER TABLE public.learning_group_members
  DROP CONSTRAINT IF EXISTS learning_group_members_student_account_id_fkey,
  ADD CONSTRAINT learning_group_members_student_account_id_fkey
    FOREIGN KEY (student_account_id) REFERENCES public.user_accounts(id) ON DELETE SET NULL;

ALTER TABLE public.group_task_assignments
  ALTER COLUMN student_account_id DROP NOT NULL;
ALTER TABLE public.group_task_assignments
  DROP CONSTRAINT IF EXISTS group_task_assignments_student_account_id_fkey,
  ADD CONSTRAINT group_task_assignments_student_account_id_fkey
    FOREIGN KEY (student_account_id) REFERENCES public.user_accounts(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_retained_content_item_lookup
  ON public.retained_content(content_type, content_id);

-- Aligns the database schema with the repo's migration history after a production drift review.
--
-- Production already holds data; this migration never drops a column, table or row.
-- Every statement is idempotent: where production already matches, nothing changes.
-- Direction: where the repo and production disagree on account deletion, the repo's
-- data-keeping behaviour wins (owner/student links become SET NULL and nullable, so rows
-- such as groups, members and tasks survive an account deletion instead of cascading away).

-- 1. Ownership links keep their rows when a user account is deleted (repo migration 20261118010000).
ALTER TABLE public.learning_groups ALTER COLUMN owner_account_id DROP NOT NULL;
ALTER TABLE public.learning_groups DROP CONSTRAINT IF EXISTS learning_groups_owner_account_id_fkey;
ALTER TABLE public.learning_groups
    ADD CONSTRAINT learning_groups_owner_account_id_fkey
    FOREIGN KEY (owner_account_id) REFERENCES public.user_accounts (id) ON DELETE SET NULL;

ALTER TABLE public.learning_group_members ALTER COLUMN student_account_id DROP NOT NULL;
ALTER TABLE public.learning_group_members DROP CONSTRAINT IF EXISTS learning_group_members_student_account_id_fkey;
ALTER TABLE public.learning_group_members
    ADD CONSTRAINT learning_group_members_student_account_id_fkey
    FOREIGN KEY (student_account_id) REFERENCES public.user_accounts (id) ON DELETE SET NULL;

ALTER TABLE public.group_learning_tasks ALTER COLUMN created_by_account_id DROP NOT NULL;
ALTER TABLE public.group_learning_tasks DROP CONSTRAINT IF EXISTS group_learning_tasks_created_by_account_id_fkey;
ALTER TABLE public.group_learning_tasks
    ADD CONSTRAINT group_learning_tasks_created_by_account_id_fkey
    FOREIGN KEY (created_by_account_id) REFERENCES public.user_accounts (id) ON DELETE SET NULL;

ALTER TABLE public.group_task_assignments ALTER COLUMN student_account_id DROP NOT NULL;
ALTER TABLE public.group_task_assignments DROP CONSTRAINT IF EXISTS group_task_assignments_student_account_id_fkey;
ALTER TABLE public.group_task_assignments
    ADD CONSTRAINT group_task_assignments_student_account_id_fkey
    FOREIGN KEY (student_account_id) REFERENCES public.user_accounts (id) ON DELETE SET NULL;

ALTER TABLE public.personal_learning_tasks ALTER COLUMN owner_account_id DROP NOT NULL;
ALTER TABLE public.personal_learning_tasks DROP CONSTRAINT IF EXISTS personal_learning_tasks_owner_account_id_fkey;
ALTER TABLE public.personal_learning_tasks
    ADD CONSTRAINT personal_learning_tasks_owner_account_id_fkey
    FOREIGN KEY (owner_account_id) REFERENCES public.user_accounts (id) ON DELETE SET NULL;

-- 2. Integer primary keys that the repo declares as bigint (widening only, no data change).
ALTER TABLE public.former_user_content_removal_requests ALTER COLUMN id TYPE BIGINT;
ALTER SEQUENCE public.former_user_content_removal_requests_id_seq AS BIGINT;
ALTER TABLE public.former_user_content_tokens ALTER COLUMN id TYPE BIGINT;
ALTER SEQUENCE public.former_user_content_tokens_id_seq AS BIGINT;
ALTER TABLE public.retained_content ALTER COLUMN id TYPE BIGINT;
ALTER SEQUENCE public.retained_content_id_seq AS BIGINT;

-- 3. Auto-increment keys. Production uses a sequence default on these ids. A clean database
--    may have created them as identity columns, so an identity is converted to the same
--    sequence default (production is already in that state, so only the no-op path runs there).
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['email_verification_tokens', 'password_reset_requests', 'password_reset_tokens'] LOOP
        IF EXISTS (
            SELECT 1 FROM pg_attribute
            WHERE attrelid = format('public.%I', t)::regclass AND attname = 'id' AND attidentity <> ''
        ) THEN
            EXECUTE format('ALTER TABLE public.%I ALTER COLUMN id DROP IDENTITY', t);
        END IF;
        EXECUTE format('CREATE SEQUENCE IF NOT EXISTS public.%I OWNED BY public.%I.id', t || '_id_seq', t);
        EXECUTE format('ALTER TABLE public.%I ALTER COLUMN id SET DEFAULT nextval(%L::regclass)',
                       t, 'public.' || t || '_id_seq');
    END LOOP;
END $$;

-- 4. Column defaults the repo migrations declare (no existing value changes).
ALTER TABLE public.account_deletion_requests
    ALTER COLUMN reason SET DEFAULT '',
    ALTER COLUMN status SET DEFAULT 'pending',
    ALTER COLUMN requested_option SET DEFAULT 'complete',
    ALTER COLUMN notification_status SET DEFAULT 'not_sent',
    ALTER COLUMN requested_account_action SET DEFAULT 'delete_account',
    ALTER COLUMN requested_content_action SET DEFAULT 'delete_all',
    ALTER COLUMN requested_content_ids SET DEFAULT '[]',
    ALTER COLUMN requested_visibility SET DEFAULT 'visible',
    ALTER COLUMN requested_anonymize_content SET DEFAULT true,
    ALTER COLUMN former_user_link_status SET DEFAULT 'not_sent';

ALTER TABLE public.content_reports
    ALTER COLUMN description SET DEFAULT '',
    ALTER COLUMN status SET DEFAULT 'pending',
    ALTER COLUMN review_note SET DEFAULT '';

ALTER TABLE public.former_user_content_removal_requests
    ALTER COLUMN selected_content SET DEFAULT '[]',
    ALTER COLUMN status SET DEFAULT 'pending',
    ALTER COLUMN review_note SET DEFAULT '';

ALTER TABLE public.managed_subjects ALTER COLUMN active SET DEFAULT true;

ALTER TABLE public.password_reset_requests
    ALTER COLUMN status SET DEFAULT 'pending',
    ALTER COLUMN requested_ip SET DEFAULT '',
    ALTER COLUMN requested_user_agent SET DEFAULT '',
    ALTER COLUMN review_note SET DEFAULT '';

ALTER TABLE public.retained_content
    ALTER COLUMN visibility SET DEFAULT 'visible',
    ALTER COLUMN anonymized SET DEFAULT false;

-- 5. CHECK constraints the repo migrations declare. Production rows are all valid for these
--    values; the tables involved are small, so each check is validated when it is added.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_final_account_action_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_final_account_action_check
            CHECK (final_account_action IS NULL OR final_account_action = 'delete_account');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_final_content_action_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_final_content_action_check
            CHECK (final_content_action IS NULL OR final_content_action IN ('account_only', 'delete_selected', 'delete_all', 'retain_all'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_final_option_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_final_option_check
            CHECK (final_option IS NULL OR final_option IN ('anonymize', 'complete'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_final_visibility_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_final_visibility_check
            CHECK (final_visibility IS NULL OR final_visibility IN ('visible', 'hidden'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_notification_status_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_notification_status_check
            CHECK (notification_status IN ('not_sent', 'sent', 'not_configured', 'failed'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_requested_account_action_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_requested_account_action_check
            CHECK (requested_account_action = 'delete_account');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_requested_content_action_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_requested_content_action_check
            CHECK (requested_content_action IN ('account_only', 'delete_selected', 'delete_all', 'retain_all'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_requested_option_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_requested_option_check
            CHECK (requested_option IN ('anonymize', 'complete'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_requested_visibility_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_requested_visibility_check
            CHECK (requested_visibility IN ('visible', 'hidden'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_requests_account_role_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_requests_account_role_check
            CHECK (account_role IN ('student', 'tutor'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'account_deletion_requests_status_check') THEN
        ALTER TABLE public.account_deletion_requests ADD CONSTRAINT account_deletion_requests_status_check
            CHECK (status IN ('pending', 'approved', 'rejected'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'password_reset_requests_account_role_check') THEN
        ALTER TABLE public.password_reset_requests ADD CONSTRAINT password_reset_requests_account_role_check
            CHECK (account_role IN ('student', 'tutor'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'password_reset_requests_status_check') THEN
        ALTER TABLE public.password_reset_requests ADD CONSTRAINT password_reset_requests_status_check
            CHECK (status IN ('pending', 'approved', 'rejected', 'completed'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'former_user_content_removal_requests_status_check') THEN
        ALTER TABLE public.former_user_content_removal_requests ADD CONSTRAINT former_user_content_removal_requests_status_check
            CHECK (status IN ('pending', 'approved', 'rejected'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'retained_content_visibility_check') THEN
        ALTER TABLE public.retained_content ADD CONSTRAINT retained_content_visibility_check
            CHECK (visibility IN ('visible', 'hidden'));
    END IF;
END $$;

-- 6. Indexes that production has under these names (repo-only duplicates are removed).
CREATE INDEX IF NOT EXISTS ix_password_reset_requests_account_id ON public.password_reset_requests (account_id);
CREATE INDEX IF NOT EXISTS ix_password_reset_requests_status ON public.password_reset_requests (status);
CREATE INDEX IF NOT EXISTS ix_former_user_content_removal_requests_deletion_request_id
    ON public.former_user_content_removal_requests (deletion_request_id);
CREATE INDEX IF NOT EXISTS ix_former_user_content_removal_requests_status
    ON public.former_user_content_removal_requests (status);
DROP INDEX IF EXISTS public.ix_former_user_content_removal_status;
CREATE INDEX IF NOT EXISTS ix_former_user_content_tokens_deletion_request_id
    ON public.former_user_content_tokens (deletion_request_id);
CREATE INDEX IF NOT EXISTS ix_former_user_content_tokens_expires_at ON public.former_user_content_tokens (expires_at);
DROP INDEX IF EXISTS public.ix_former_user_content_tokens_expiry;
CREATE INDEX IF NOT EXISTS ix_retained_content_deletion_request_id ON public.retained_content (deletion_request_id);
DROP INDEX IF EXISTS public.ix_retained_content_item_lookup;

-- 7. First Admin protection: the repo's earlier definition returned NULL on DELETE, which silently
--    cancelled deletes on a clean database. This is the corrected body production already runs.
CREATE OR REPLACE FUNCTION public.tutorinn_protect_first_admin()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $function$
BEGIN
    IF OLD.is_first_admin IS TRUE THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION
                'The designated First Admin account cannot be deleted';
        END IF;

        IF NEW.is_first_admin IS NOT TRUE
           OR NEW.role <> 'admin'
           OR NEW.status <> 'active' THEN
            RAISE EXCEPTION
                'The designated First Admin account cannot be demoted or disabled';
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$function$;

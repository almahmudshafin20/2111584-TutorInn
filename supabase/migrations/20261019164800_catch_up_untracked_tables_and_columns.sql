-- Catch-up for production schema that was created outside the migration files
-- (SQLAlchemy create_all on app startup, plus manual column additions).
-- Every statement is idempotent: on production, where these objects already exist, nothing changes.
-- On a clean database this recreates the same tables, columns, constraints and indexes that
-- production has, so the replay matches production's schema before later migrations run.

CREATE TABLE IF NOT EXISTS public.user_accounts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    is_first_admin BOOLEAN NOT NULL DEFAULT false,
    email_verified_at VARCHAR(40)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_accounts_email ON public.user_accounts (email);
CREATE INDEX IF NOT EXISTS ix_user_accounts_id ON public.user_accounts (id);
CREATE INDEX IF NOT EXISTS ix_user_accounts_role ON public.user_accounts (role);
CREATE INDEX IF NOT EXISTS ix_user_accounts_status ON public.user_accounts (status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_accounts_first_admin ON public.user_accounts (is_first_admin) WHERE is_first_admin IS TRUE;

-- Columns added to the profile tables created by 20261019164750_create_tutorinn_profile_tables.sql.
ALTER TABLE public.students
    ADD COLUMN IF NOT EXISTS subjects_json TEXT,
    ADD COLUMN IF NOT EXISTS phone_number VARCHAR(32) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES public.user_accounts (id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_students_account_id ON public.students (account_id) WHERE account_id IS NOT NULL;

ALTER TABLE public.tutors
    ADD COLUMN IF NOT EXISTS subjects_json TEXT,
    ADD COLUMN IF NOT EXISTS phone_number VARCHAR(32) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES public.user_accounts (id),
    ADD COLUMN IF NOT EXISTS availability VARCHAR(255) NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_tutors_account_id ON public.tutors (account_id) WHERE account_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.learning_groups (
    id SERIAL PRIMARY KEY,
    owner_account_id INTEGER NOT NULL REFERENCES public.user_accounts (id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(1000) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_learning_groups_id ON public.learning_groups (id);
CREATE INDEX IF NOT EXISTS ix_learning_groups_owner_account_id ON public.learning_groups (owner_account_id);

CREATE TABLE IF NOT EXISTS public.learning_group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES public.learning_groups (id) ON DELETE CASCADE,
    student_account_id INTEGER NOT NULL REFERENCES public.user_accounts (id) ON DELETE CASCADE,
    can_create_tasks BOOLEAN NOT NULL,
    can_edit_tasks BOOLEAN NOT NULL,
    can_assign_tasks BOOLEAN NOT NULL,
    joined_at VARCHAR(40) NOT NULL,
    CONSTRAINT uq_group_student_member UNIQUE (group_id, student_account_id)
);
CREATE INDEX IF NOT EXISTS ix_learning_group_members_id ON public.learning_group_members (id);
CREATE INDEX IF NOT EXISTS ix_learning_group_members_group_id ON public.learning_group_members (group_id);
CREATE INDEX IF NOT EXISTS ix_learning_group_members_student_account_id ON public.learning_group_members (student_account_id);

CREATE TABLE IF NOT EXISTS public.group_learning_tasks (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES public.learning_groups (id) ON DELETE CASCADE,
    created_by_account_id INTEGER NOT NULL REFERENCES public.user_accounts (id),
    title VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    due_date DATE,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    video_url VARCHAR(2048)
);
CREATE INDEX IF NOT EXISTS ix_group_learning_tasks_id ON public.group_learning_tasks (id);
CREATE INDEX IF NOT EXISTS ix_group_learning_tasks_group_id ON public.group_learning_tasks (group_id);
CREATE INDEX IF NOT EXISTS ix_group_learning_tasks_created_by_account_id ON public.group_learning_tasks (created_by_account_id);

CREATE TABLE IF NOT EXISTS public.group_task_assignments (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES public.group_learning_tasks (id) ON DELETE CASCADE,
    student_account_id INTEGER NOT NULL REFERENCES public.user_accounts (id) ON DELETE CASCADE,
    completed BOOLEAN NOT NULL,
    assigned_at VARCHAR(40) NOT NULL,
    completed_at VARCHAR(40),
    CONSTRAINT uq_group_task_student_assignment UNIQUE (task_id, student_account_id)
);
CREATE INDEX IF NOT EXISTS ix_group_task_assignments_id ON public.group_task_assignments (id);
CREATE INDEX IF NOT EXISTS ix_group_task_assignments_task_id ON public.group_task_assignments (task_id);
CREATE INDEX IF NOT EXISTS ix_group_task_assignments_student_account_id ON public.group_task_assignments (student_account_id);

CREATE TABLE IF NOT EXISTS public.learning_posts (
    id SERIAL PRIMARY KEY,
    post_type VARCHAR(12) NOT NULL,
    author_name VARCHAR(120) NOT NULL,
    subject VARCHAR(120) NOT NULL,
    level VARCHAR(80) NOT NULL,
    experience VARCHAR(500) NOT NULL,
    availability VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    fee DOUBLE PRECISION NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    student_confirmed BOOLEAN NOT NULL,
    tutor_confirmed BOOLEAN NOT NULL,
    student_response VARCHAR(20) NOT NULL DEFAULT 'No response',
    tutor_response VARCHAR(20) NOT NULL DEFAULT 'No response',
    author_profile_id INTEGER,
    author_profile_type VARCHAR(12),
    subjects_json TEXT,
    created_at VARCHAR(40)
);
CREATE INDEX IF NOT EXISTS ix_learning_posts_id ON public.learning_posts (id);
CREATE INDEX IF NOT EXISTS ix_learning_posts_post_type ON public.learning_posts (post_type);
CREATE INDEX IF NOT EXISTS ix_learning_posts_subject ON public.learning_posts (subject);
CREATE INDEX IF NOT EXISTS ix_learning_posts_created_at ON public.learning_posts (created_at);

CREATE TABLE IF NOT EXISTS public.interest_responses (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL,
    profile_id INTEGER NOT NULL,
    profile_type VARCHAR(12) NOT NULL,
    response VARCHAR(20) NOT NULL,
    review_status VARCHAR(20) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    CONSTRAINT uq_interest_post_profile UNIQUE (post_id, profile_type, profile_id)
);
CREATE INDEX IF NOT EXISTS ix_interest_responses_id ON public.interest_responses (id);
CREATE INDEX IF NOT EXISTS ix_interest_responses_post_id ON public.interest_responses (post_id);
CREATE INDEX IF NOT EXISTS ix_interest_responses_profile_id ON public.interest_responses (profile_id);
CREATE INDEX IF NOT EXISTS ix_interest_responses_profile_type ON public.interest_responses (profile_type);

CREATE TABLE IF NOT EXISTS public.personal_learning_tasks (
    id SERIAL PRIMARY KEY,
    owner_account_id INTEGER NOT NULL REFERENCES public.user_accounts (id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(60),
    due_date DATE,
    completed BOOLEAN NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_personal_learning_tasks_id ON public.personal_learning_tasks (id);
CREATE INDEX IF NOT EXISTS ix_personal_learning_tasks_owner_account_id ON public.personal_learning_tasks (owner_account_id);
CREATE INDEX IF NOT EXISTS ix_personal_learning_tasks_category ON public.personal_learning_tasks (category);
CREATE INDEX IF NOT EXISTS ix_personal_tasks_owner_category ON public.personal_learning_tasks (owner_account_id, category);
CREATE INDEX IF NOT EXISTS ix_personal_tasks_owner_due_date ON public.personal_learning_tasks (owner_account_id, due_date);

CREATE TABLE IF NOT EXISTS public.refresh_sessions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES public.user_accounts (id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    family_id VARCHAR(36) NOT NULL,
    csrf_token_hash VARCHAR(64) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    last_used_at VARCHAR(40) NOT NULL,
    expires_at VARCHAR(40) NOT NULL,
    revoked_at VARCHAR(40),
    replaced_by VARCHAR(64),
    user_agent VARCHAR(512) NOT NULL,
    ip_address VARCHAR(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_refresh_sessions_id ON public.refresh_sessions (id);
CREATE INDEX IF NOT EXISTS ix_refresh_sessions_account_id ON public.refresh_sessions (account_id);
CREATE INDEX IF NOT EXISTS ix_refresh_sessions_expires_at ON public.refresh_sessions (expires_at);
CREATE INDEX IF NOT EXISTS ix_refresh_sessions_family_id ON public.refresh_sessions (family_id);

CREATE TABLE IF NOT EXISTS public.security_events (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES public.user_accounts (id),
    event_type VARCHAR(64) NOT NULL,
    attempted_email VARCHAR(255) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    user_agent VARCHAR(512) NOT NULL,
    details TEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_security_events_id ON public.security_events (id);
CREATE INDEX IF NOT EXISTS ix_security_events_account_id ON public.security_events (account_id);
CREATE INDEX IF NOT EXISTS ix_security_events_event_type ON public.security_events (event_type);

CREATE TABLE IF NOT EXISTS public.tutor_verifications (
    id SERIAL PRIMARY KEY,
    tutor_id INTEGER NOT NULL REFERENCES public.tutors (id) ON DELETE CASCADE,
    status VARCHAR(16) NOT NULL,
    reviewer_account_id INTEGER REFERENCES public.user_accounts (id),
    reviewed_at VARCHAR(40),
    review_note VARCHAR(1000) NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tutor_verifications_tutor_id ON public.tutor_verifications (tutor_id);
CREATE INDEX IF NOT EXISTS ix_tutor_verifications_status ON public.tutor_verifications (status);

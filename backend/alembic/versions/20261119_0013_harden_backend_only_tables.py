"""Harden backend-only token tables and pin the First Admin trigger search path."""

from alembic import context, op


revision = "20261119_0013"
down_revision = "20261118_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.get_context().dialect.name != "postgresql":
        return

    op.execute("""
        ALTER TABLE public.email_verification_tokens ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.password_reset_requests ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;

        REVOKE ALL PRIVILEGES ON TABLE
            public.email_verification_tokens,
            public.password_reset_requests,
            public.password_reset_tokens
        FROM PUBLIC;

        REVOKE ALL PRIVILEGES ON SEQUENCE
            public.email_verification_tokens_id_seq,
            public.password_reset_requests_id_seq,
            public.password_reset_tokens_id_seq
        FROM PUBLIC;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.email_verification_tokens, public.password_reset_requests, public.password_reset_tokens FROM anon';
                EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE public.email_verification_tokens_id_seq, public.password_reset_requests_id_seq, public.password_reset_tokens_id_seq FROM anon';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.email_verification_tokens, public.password_reset_requests, public.password_reset_tokens FROM authenticated';
                EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE public.email_verification_tokens_id_seq, public.password_reset_requests_id_seq, public.password_reset_tokens_id_seq FROM authenticated';
            END IF;
        END
        $$;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.tutorinn_protect_first_admin()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF OLD.is_first_admin IS TRUE THEN
                IF TG_OP = 'DELETE' THEN
                    RAISE EXCEPTION 'The designated First Admin account cannot be deleted';
                END IF;
                IF NEW.is_first_admin IS NOT TRUE
                   OR NEW.role <> 'admin'
                   OR NEW.status <> 'active' THEN
                    RAISE EXCEPTION 'The designated First Admin account cannot be demoted or disabled';
                END IF;
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $function$;
    """)


def downgrade() -> None:
    # Keep the trigger protection and tightened privileges in place on downgrade.
    pass

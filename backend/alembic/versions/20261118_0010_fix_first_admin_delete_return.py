"""Fix BEFORE DELETE return behavior while preserving First Admin protection."""

from alembic import context, op


revision = "20261118_0010"
down_revision = "20261118_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.get_context().dialect.name != "postgresql":
        return

    op.execute("""
        CREATE OR REPLACE FUNCTION public.tutorinn_protect_first_admin()
        RETURNS trigger
        LANGUAGE plpgsql
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
    # Keep the corrected protection function in place on downgrade.
    pass

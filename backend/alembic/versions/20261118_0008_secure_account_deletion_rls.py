"""Enable RLS and revoke browser access on account-deletion privacy tables."""

from alembic import context, op
import sqlalchemy as sa


revision = "20261118_0008"
down_revision = "20261118_0007"
branch_labels = None
depends_on = None

PRIVATE_TABLES = (
    "account_deletion_requests",
    "retained_content",
    "former_user_content_tokens",
    "former_user_content_removal_requests",
)


def upgrade():
    dialect_name = context.get_context().dialect.name
    if dialect_name != "postgresql":
        return

    if context.is_offline_mode():
        for table in PRIVATE_TABLES:
            op.execute(sa.text(
                f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY'
            ))
            op.execute(sa.text(
                f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM PUBLIC'
            ))
            # Supabase roles are optional in ordinary PostgreSQL installations.
            # Resolve their presence at SQL execution time in offline-generated scripts.
            op.execute(sa.text(f"""
                DO $
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM anon';
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM authenticated';
                    END IF;
                END
                $;
            """))
        return

    bind = op.get_bind()
    existing_roles = set(bind.execute(sa.text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
    )).scalars())

    for table in PRIVATE_TABLES:
        op.execute(sa.text(
            f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY'
        ))
        op.execute(sa.text(
            f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM PUBLIC'
        ))
        for role in ("anon", "authenticated"):
            if role in existing_roles:
                op.execute(sa.text(
                    f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM "{role}"'
                ))


def downgrade():
    # Privacy protections must not be silently removed by an application rollback.
    pass

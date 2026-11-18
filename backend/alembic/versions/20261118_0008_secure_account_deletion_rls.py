"""Enable RLS and revoke browser access on account-deletion privacy tables."""

from alembic import op
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
    if op.get_bind().dialect.name != "postgresql":
        return

    for table in PRIVATE_TABLES:
        op.execute(sa.text(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(
            f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" '
            'FROM PUBLIC, anon, authenticated'
        ))


def downgrade():
    # Privacy protections must not be silently removed by an application rollback.
    pass

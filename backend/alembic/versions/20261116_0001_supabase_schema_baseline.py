"""Record the existing Supabase-managed schema as the Alembic baseline.

Revision ID: 20261116_0001
Revises:
"""
revision = "20261116_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing schema is managed by the committed Supabase SQL migration history.
    # This marker intentionally performs no DDL; stamp only after schema review.
    pass


def downgrade() -> None:
    # A baseline marker must never drop the pre-existing application schema.
    pass

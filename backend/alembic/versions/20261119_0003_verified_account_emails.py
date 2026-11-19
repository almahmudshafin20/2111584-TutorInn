"""Track verified account email addresses and expiring verification tokens.

Revision ID: 20261119_0003
Revises: 20261119_0002
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20261119_0003"
down_revision = "20261119_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_accounts", sa.Column("email_verified_at", sa.String(length=40), nullable=True))
    op.add_column("user_accounts", sa.Column("email_verification_token_hash", sa.String(length=64), nullable=True))
    op.add_column("user_accounts", sa.Column("email_verification_expires_at", sa.String(length=40), nullable=True))
    op.create_index(
        "uq_user_accounts_email_verification_token_hash",
        "user_accounts",
        ["email_verification_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_user_accounts_email_verification_token_hash", table_name="user_accounts")
    op.drop_column("user_accounts", "email_verification_expires_at")
    op.drop_column("user_accounts", "email_verification_token_hash")
    op.drop_column("user_accounts", "email_verified_at")

"""Add approval-gated password reset requests.

Revision ID: 20261119_0002
Revises: 20261116_0001
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20261119_0002"
down_revision = "20261116_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("user_accounts.id"), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("requested_at", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id"), nullable=True),
        sa.Column("reviewed_at", sa.String(length=40), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        sa.Column("token_expires_at", sa.String(length=40), nullable=True),
        sa.Column("token_used_at", sa.String(length=40), nullable=True),
        sa.Column("delivery_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_requests_token_hash"),
    )
    op.create_index("ix_password_reset_requests_id", "password_reset_requests", ["id"])
    op.create_index("ix_password_reset_requests_account_id", "password_reset_requests", ["account_id"])
    op.create_index("ix_password_reset_requests_email", "password_reset_requests", ["email"])
    op.create_index("ix_password_reset_requests_status", "password_reset_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_requests_status", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_email", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_account_id", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_id", table_name="password_reset_requests")
    op.drop_table("password_reset_requests")

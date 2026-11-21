"""Add approved, user-controlled password reset workflow."""

from alembic import op
import sqlalchemy as sa

revision = "20261118_0011"
down_revision = "20261118_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_email", sa.String(255), nullable=False),
        sa.Column("account_role", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.String(40), nullable=False),
        sa.Column("requested_ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("requested_user_agent", sa.String(512), nullable=False, server_default=""),
        sa.Column("reviewed_by_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.String(40), nullable=True),
        sa.Column("review_note", sa.String(1000), nullable=False, server_default=""),
    )
    op.create_index("ix_password_reset_requests_account_id", "password_reset_requests", ["account_id"])
    op.create_index("ix_password_reset_requests_status", "password_reset_requests", ["status"])
    op.create_index("ix_password_reset_requests_status_requested", "password_reset_requests", ["status", "requested_at"])
    op.create_index("ix_password_reset_requests_account_status", "password_reset_requests", ["account_id", "status"])
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("password_reset_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.Column("used_at", sa.String(40), nullable=True),
        sa.Column("invalidated_at", sa.String(40), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_request_id", "password_reset_tokens", ["request_id"])
    op.create_index("ix_password_reset_tokens_account_id", "password_reset_tokens", ["account_id"])
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_account_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_request_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_password_reset_requests_account_status", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_status_requested", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_status", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_account_id", table_name="password_reset_requests")
    op.drop_table("password_reset_requests")

"""Persist verified email ownership and single-use verification tokens."""
from alembic import op
import sqlalchemy as sa

revision = "20261118_0012"
down_revision = "20261118_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_accounts", sa.Column("email_verified_at", sa.String(40), nullable=True))
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.Column("used_at", sa.String(40), nullable=True),
        sa.Column("invalidated_at", sa.String(40), nullable=True),
    )
    op.create_index("ix_email_verification_tokens_account_id", "email_verification_tokens", ["account_id"])
    op.create_index("ix_email_verification_tokens_expires_at", "email_verification_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_email_verification_tokens_expires_at", table_name="email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_account_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_column("user_accounts", "email_verified_at")

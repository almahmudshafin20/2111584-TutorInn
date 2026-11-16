"""Add persistent tutor verification workflow."""
from alembic import op
import sqlalchemy as sa

revision = "20261116_0004"
down_revision = "20261116_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tutor_verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutor_id", sa.Integer(), sa.ForeignKey("tutors.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("reviewer_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id"), nullable=True),
        sa.Column("reviewed_at", sa.String(40), nullable=True),
        sa.Column("review_note", sa.String(1000), nullable=False, server_default=""),
    )
    op.create_index("ix_tutor_verifications_tutor_id", "tutor_verifications", ["tutor_id"])
    op.create_index("ix_tutor_verifications_status", "tutor_verifications", ["status"])


def downgrade():
    op.drop_index("ix_tutor_verifications_status", table_name="tutor_verifications")
    op.drop_index("ix_tutor_verifications_tutor_id", table_name="tutor_verifications")
    op.drop_table("tutor_verifications")

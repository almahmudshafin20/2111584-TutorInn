"""Add Admin-managed subjects and user content reports."""

from alembic import op
import sqlalchemy as sa

revision = "20261116_0006"
down_revision = "20261116_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "managed_subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.UniqueConstraint("name", name="uq_managed_subject_name"),
    )
    op.create_index("ix_managed_subjects_id", "managed_subjects", ["id"])
    op.create_index("ix_managed_subjects_active", "managed_subjects", ["active"])
    op.create_table(
        "content_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(length=24), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("review_note", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("reviewed_by_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id"), nullable=True),
        sa.Column("reviewed_at", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
    )
    op.create_index("ix_content_reports_id", "content_reports", ["id"])
    op.create_index("ix_content_reports_reporter_account_id", "content_reports", ["reporter_account_id"])
    op.create_index("ix_content_reports_status", "content_reports", ["status"])
    op.create_index("ix_content_reports_status_created", "content_reports", ["status", "created_at"])
    op.create_index("ix_content_reports_target", "content_reports", ["target_type", "target_id"])
    op.create_index("ix_content_reports_reporter_created", "content_reports", ["reporter_account_id", "created_at"])


def downgrade():
    op.drop_index("ix_content_reports_reporter_created", table_name="content_reports")
    op.drop_index("ix_content_reports_target", table_name="content_reports")
    op.drop_index("ix_content_reports_status_created", table_name="content_reports")
    op.drop_index("ix_content_reports_status", table_name="content_reports")
    op.drop_index("ix_content_reports_reporter_account_id", table_name="content_reports")
    op.drop_index("ix_content_reports_id", table_name="content_reports")
    op.drop_table("content_reports")
    op.drop_index("ix_managed_subjects_active", table_name="managed_subjects")
    op.drop_index("ix_managed_subjects_id", table_name="managed_subjects")
    op.drop_table("managed_subjects")

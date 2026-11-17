"""Create tutor-owned learning groups and member assignments."""
from alembic import op
import sqlalchemy as sa

revision = "20261116_0003"
down_revision = "20261116_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learning_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_learning_groups_id", "learning_groups", ["id"])
    op.create_index("ix_learning_groups_owner_account_id", "learning_groups", ["owner_account_id"])
    op.create_table(
        "learning_group_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("learning_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("can_create_tasks", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_edit_tasks", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_assign_tasks", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("joined_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("group_id", "student_account_id", name="uq_group_student_member"),
    )
    op.create_index("ix_learning_group_members_id", "learning_group_members", ["id"])
    op.create_index("ix_learning_group_members_group_id", "learning_group_members", ["group_id"])
    op.create_index("ix_learning_group_members_student_account_id", "learning_group_members", ["student_account_id"])
    op.create_table(
        "group_learning_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("learning_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_group_learning_tasks_id", "group_learning_tasks", ["id"])
    op.create_index("ix_group_learning_tasks_group_id", "group_learning_tasks", ["group_id"])
    op.create_index("ix_group_learning_tasks_created_by_account_id", "group_learning_tasks", ["created_by_account_id"])
    op.create_table(
        "group_task_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("group_learning_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("assigned_at", sa.String(40), nullable=False),
        sa.Column("completed_at", sa.String(40), nullable=True),
        sa.UniqueConstraint("task_id", "student_account_id", name="uq_group_task_student_assignment"),
    )
    op.create_index("ix_group_task_assignments_id", "group_task_assignments", ["id"])
    op.create_index("ix_group_task_assignments_task_id", "group_task_assignments", ["task_id"])
    op.create_index("ix_group_task_assignments_student_account_id", "group_task_assignments", ["student_account_id"])


def downgrade():
    op.drop_table("group_task_assignments")
    op.drop_table("group_learning_tasks")
    op.drop_table("learning_group_members")
    op.drop_table("learning_groups")

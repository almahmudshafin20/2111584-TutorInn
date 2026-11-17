"""Create private personal learning tasks."""
from alembic import op
import sqlalchemy as sa
revision="20261116_0002"
down_revision="20261116_0001"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("personal_learning_tasks",
        sa.Column("id",sa.Integer(),primary_key=True,nullable=False),
        sa.Column("owner_account_id",sa.Integer(),sa.ForeignKey("user_accounts.id",ondelete="CASCADE"),nullable=False),
        sa.Column("title",sa.String(160),nullable=False),
        sa.Column("description",sa.Text(),nullable=False,server_default=""),
        sa.Column("category",sa.String(60),nullable=True),
        sa.Column("due_date",sa.Date(),nullable=True),
        sa.Column("completed",sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column("created_at",sa.String(40),nullable=False),
        sa.Column("updated_at",sa.String(40),nullable=False))
    op.create_index("ix_personal_learning_tasks_id","personal_learning_tasks",["id"])
    op.create_index("ix_personal_learning_tasks_owner_account_id","personal_learning_tasks",["owner_account_id"])
    op.create_index("ix_personal_learning_tasks_category","personal_learning_tasks",["category"])
    op.create_index("ix_personal_tasks_owner_due_date","personal_learning_tasks",["owner_account_id","due_date"])
    op.create_index("ix_personal_tasks_owner_category","personal_learning_tasks",["owner_account_id","category"])

def downgrade():
    op.drop_index("ix_personal_tasks_owner_category",table_name="personal_learning_tasks")
    op.drop_index("ix_personal_tasks_owner_due_date",table_name="personal_learning_tasks")
    op.drop_index("ix_personal_learning_tasks_category",table_name="personal_learning_tasks")
    op.drop_index("ix_personal_learning_tasks_owner_account_id",table_name="personal_learning_tasks")
    op.drop_index("ix_personal_learning_tasks_id",table_name="personal_learning_tasks")
    op.drop_table("personal_learning_tasks")

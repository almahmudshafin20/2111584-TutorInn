"""Track creation time for new tutoring requests."""

from alembic import op
import sqlalchemy as sa

revision = "20261116_0005"
down_revision = "20261116_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("learning_posts", sa.Column("created_at", sa.String(40), nullable=True))
    op.create_index("ix_learning_posts_created_at", "learning_posts", ["created_at"])


def downgrade():
    op.drop_index("ix_learning_posts_created_at", table_name="learning_posts")
    op.drop_column("learning_posts", "created_at")

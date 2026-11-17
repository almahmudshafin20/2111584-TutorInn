"""Persist former-user verification delivery and serialize pending removal requests."""

from alembic import context, op
import sqlalchemy as sa

revision = "20261118_0007"
down_revision = "20261116_0006"
branch_labels = None
depends_on = None


def upgrade():
    # Offline SQL rendering cannot inspect a live schema. Emit the migration DDL
    # directly in that mode; online upgrades remain idempotent for schemas where
    # the matching Supabase SQL migration has already been applied.
    if context.is_offline_mode():
        op.add_column(
            "account_deletion_requests",
            sa.Column("former_user_link_status", sa.String(length=20), nullable=False, server_default="not_sent"),
        )
        op.create_index(
            "uq_former_user_removal_pending",
            "former_user_content_removal_requests",
            ["deletion_request_id"],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
            sqlite_where=sa.text("status = 'pending'"),
        )
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "account_deletion_requests" in tables:
        columns = {column["name"] for column in inspector.get_columns("account_deletion_requests")}
        if "former_user_link_status" not in columns:
            op.add_column(
                "account_deletion_requests",
                sa.Column("former_user_link_status", sa.String(length=20), nullable=False, server_default="not_sent"),
            )
    if "former_user_content_removal_requests" in tables:
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("former_user_content_removal_requests")}
        if "uq_former_user_removal_pending" not in indexes:
            op.create_index(
                "uq_former_user_removal_pending",
                "former_user_content_removal_requests",
                ["deletion_request_id"],
                unique=True,
                postgresql_where=sa.text("status = 'pending'"),
                sqlite_where=sa.text("status = 'pending'"),
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "former_user_content_removal_requests" in tables:
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("former_user_content_removal_requests")}
        if "uq_former_user_removal_pending" in indexes:
            op.drop_index("uq_former_user_removal_pending", table_name="former_user_content_removal_requests")
    if "account_deletion_requests" in tables:
        columns = {column["name"] for column in sa.inspect(bind).get_columns("account_deletion_requests")}
        if "former_user_link_status" in columns:
            op.drop_column("account_deletion_requests", "former_user_link_status")

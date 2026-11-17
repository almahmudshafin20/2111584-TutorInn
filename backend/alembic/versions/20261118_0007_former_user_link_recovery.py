"""Create account-deletion retention schema and former-user recovery safeguards."""

from alembic import context, op
import sqlalchemy as sa


revision = "20261118_0007"
down_revision = "20261116_0006"
branch_labels = None
depends_on = None


DELETION_COLUMNS = (
    sa.Column("account_id", sa.Integer(), nullable=True),
    sa.Column("account_email", sa.String(255), nullable=False, server_default=""),
    sa.Column("former_user_email", sa.String(255), nullable=True),
    sa.Column("account_role", sa.String(16), nullable=False, server_default="student"),
    sa.Column("reason", sa.String(500), nullable=False, server_default=""),
    sa.Column("requested_option", sa.String(16), nullable=False, server_default="complete"),
    sa.Column("final_option", sa.String(16), nullable=True),
    sa.Column("requested_account_action", sa.String(24), nullable=False, server_default="delete_account"),
    sa.Column("requested_content_action", sa.String(24), nullable=False, server_default="delete_all"),
    sa.Column("requested_content_ids", sa.Text(), nullable=False, server_default="[]"),
    sa.Column("requested_visibility", sa.String(12), nullable=False, server_default="visible"),
    sa.Column("requested_anonymize_content", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("final_account_action", sa.String(24), nullable=True),
    sa.Column("final_content_action", sa.String(24), nullable=True),
    sa.Column("final_content_ids", sa.Text(), nullable=True),
    sa.Column("final_visibility", sa.String(12), nullable=True),
    sa.Column("final_anonymize_content", sa.Boolean(), nullable=True),
    sa.Column("notification_status", sa.String(20), nullable=False, server_default="not_sent"),
    sa.Column("former_user_link_status", sa.String(20), nullable=False, server_default="not_sent"),
    sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
    sa.Column("requested_at", sa.String(40), nullable=False, server_default=""),
    sa.Column("reviewed_at", sa.String(40), nullable=True),
    sa.Column("reviewed_by_account_id", sa.Integer(), nullable=True),
)


def _ensure_deletion_request_table():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "account_deletion_requests" not in tables:
        op.create_table(
            "account_deletion_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            *DELETION_COLUMNS,
            sa.ForeignKeyConstraint(
                ["reviewed_by_account_id"], ["user_accounts.id"],
                name="fk_account_deletion_reviewed_by", ondelete="SET NULL",
            ),
        )
        return

    existing = {column["name"] for column in inspector.get_columns("account_deletion_requests")}
    for column in DELETION_COLUMNS:
        if column.name not in existing:
            op.add_column("account_deletion_requests", column.copy())


def _ensure_retention_tables():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "retained_content" not in tables:
        op.create_table(
            "retained_content",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("deletion_request_id", sa.Integer(), sa.ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("content_type", sa.String(32), nullable=False),
            sa.Column("content_id", sa.Integer(), nullable=False),
            sa.Column("visibility", sa.String(12), nullable=False, server_default="visible"),
            sa.Column("anonymized", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.UniqueConstraint("deletion_request_id", "content_type", "content_id", name="uq_retained_content_item"),
        )
    if "former_user_content_tokens" not in tables:
        op.create_table(
            "former_user_content_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("deletion_request_id", sa.Integer(), sa.ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.String(40), nullable=False),
            sa.Column("consumed_at", sa.String(40), nullable=True),
            sa.Column("created_at", sa.String(40), nullable=False),
        )
    if "former_user_content_removal_requests" not in tables:
        op.create_table(
            "former_user_content_removal_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("deletion_request_id", sa.Integer(), sa.ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("selected_content", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("requested_at", sa.String(40), nullable=False),
            sa.Column("reviewed_at", sa.String(40), nullable=True),
            sa.Column("reviewed_by_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("review_note", sa.String(1000), nullable=False, server_default=""),
        )


def _ensure_indexes():
    inspector = sa.inspect(op.get_bind())
    definitions = (
        ("account_deletion_requests", "ix_account_deletion_requests_account_id", ["account_id"], False, None),
        ("account_deletion_requests", "ix_account_deletion_requests_status", ["status"], False, None),
        ("account_deletion_requests", "uq_account_deletion_pending", ["account_id"], True, "status = 'pending' AND account_id IS NOT NULL"),
        ("retained_content", "ix_retained_content_deletion_request_id", ["deletion_request_id"], False, None),
        ("retained_content", "ix_retained_content_owner_request", ["deletion_request_id", "visibility"], False, None),
        ("retained_content", "ix_retained_content_item_lookup", ["content_type", "content_id"], False, None),
        ("former_user_content_tokens", "ix_former_user_content_tokens_deletion_request_id", ["deletion_request_id"], False, None),
        ("former_user_content_tokens", "ix_former_user_content_tokens_expires_at", ["expires_at"], False, None),
        ("former_user_content_removal_requests", "ix_former_user_content_removal_requests_deletion_request_id", ["deletion_request_id"], False, None),
        ("former_user_content_removal_requests", "ix_former_user_content_removal_requests_status", ["status"], False, None),
        ("former_user_content_removal_requests", "uq_former_user_removal_pending", ["deletion_request_id"], True, "status = 'pending'"),
    )
    for table, name, columns, unique, predicate in definitions:
        existing = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
        if name not in existing:
            op.create_index(
                name, table, columns, unique=unique,
                postgresql_where=sa.text(predicate) if predicate else None,
                sqlite_where=sa.text(predicate) if predicate else None,
            )


def _make_owner_references_nullable():
    bind = op.get_bind()
    dialect = bind.dialect.name
    targets = (
        ("personal_learning_tasks", "owner_account_id"),
        ("learning_groups", "owner_account_id"),
        ("learning_group_members", "student_account_id"),
        ("group_learning_tasks", "created_by_account_id"),
        ("group_task_assignments", "student_account_id"),
    )
    tables = set(sa.inspect(bind).get_table_names())
    for table, column in targets:
        if table not in tables:
            continue
        current = next((item for item in sa.inspect(bind).get_columns(table) if item["name"] == column), None)
        if current is None or current.get("nullable", True):
            continue
        if dialect == "sqlite":
            with op.batch_alter_table(table, recreate="always") as batch:
                batch.alter_column(column, existing_type=current["type"], existing_nullable=False, nullable=True)
        else:
            op.alter_column(table, column, existing_type=current["type"], existing_nullable=False, nullable=True)
            if dialect == "postgresql":
                fk = next((item for item in sa.inspect(bind).get_foreign_keys(table) if item.get("constrained_columns") == [column]), None)
                if fk:
                    if fk.get("name"):
                        op.drop_constraint(fk["name"], table, type_="foreignkey")
                    op.create_foreign_key(
                        fk.get("name") or "fk_" + table + "_" + column,
                        table, "user_accounts", [column], ["id"], ondelete="SET NULL",
                    )


def upgrade():
    if context.is_offline_mode():
        op.create_table(
            "account_deletion_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            *DELETION_COLUMNS,
            sa.ForeignKeyConstraint(["reviewed_by_account_id"], ["user_accounts.id"], name="fk_account_deletion_reviewed_by", ondelete="SET NULL"),
        )
        op.create_table(
            "retained_content",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("deletion_request_id", sa.Integer(), sa.ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("content_type", sa.String(32), nullable=False),
            sa.Column("content_id", sa.Integer(), nullable=False),
            sa.Column("visibility", sa.String(12), nullable=False, server_default="visible"),
            sa.Column("anonymized", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.UniqueConstraint("deletion_request_id", "content_type", "content_id", name="uq_retained_content_item"),
        )
        op.create_table(
            "former_user_content_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("deletion_request_id", sa.Integer(), sa.ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.String(40), nullable=False),
            sa.Column("consumed_at", sa.String(40), nullable=True),
            sa.Column("created_at", sa.String(40), nullable=False),
        )
        op.create_table(
            "former_user_content_removal_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("deletion_request_id", sa.Integer(), sa.ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("selected_content", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("requested_at", sa.String(40), nullable=False),
            sa.Column("reviewed_at", sa.String(40), nullable=True),
            sa.Column("reviewed_by_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("review_note", sa.String(1000), nullable=False, server_default=""),
        )
        _ensure_indexes_offline()
        return

    _ensure_deletion_request_table()
    _ensure_retention_tables()
    _ensure_indexes()
    _make_owner_references_nullable()


def _ensure_indexes_offline():
    definitions = (
        ("account_deletion_requests", "ix_account_deletion_requests_account_id", ["account_id"], False, None),
        ("account_deletion_requests", "ix_account_deletion_requests_status", ["status"], False, None),
        ("account_deletion_requests", "uq_account_deletion_pending", ["account_id"], True, "status = 'pending' AND account_id IS NOT NULL"),
        ("retained_content", "ix_retained_content_deletion_request_id", ["deletion_request_id"], False, None),
        ("retained_content", "ix_retained_content_owner_request", ["deletion_request_id", "visibility"], False, None),
        ("retained_content", "ix_retained_content_item_lookup", ["content_type", "content_id"], False, None),
        ("former_user_content_tokens", "ix_former_user_content_tokens_deletion_request_id", ["deletion_request_id"], False, None),
        ("former_user_content_tokens", "ix_former_user_content_tokens_expires_at", ["expires_at"], False, None),
        ("former_user_content_removal_requests", "ix_former_user_content_removal_requests_deletion_request_id", ["deletion_request_id"], False, None),
        ("former_user_content_removal_requests", "ix_former_user_content_removal_requests_status", ["status"], False, None),
        ("former_user_content_removal_requests", "uq_former_user_removal_pending", ["deletion_request_id"], True, "status = 'pending'"),
    )
    for table, name, columns, unique, predicate in definitions:
        op.create_index(
            name, table, columns, unique=unique,
            postgresql_where=sa.text(predicate) if predicate else None,
            sqlite_where=sa.text(predicate) if predicate else None,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "former_user_content_removal_requests" in tables:
        indexes = {item["name"] for item in inspector.get_indexes("former_user_content_removal_requests")}
        if "uq_former_user_removal_pending" in indexes:
            op.drop_index("uq_former_user_removal_pending", table_name="former_user_content_removal_requests")
    if "former_user_content_removal_requests" in tables:
        op.drop_table("former_user_content_removal_requests")
    if "former_user_content_tokens" in tables:
        op.drop_table("former_user_content_tokens")
    if "retained_content" in tables:
        op.drop_table("retained_content")
    # Keep the durable account-deletion receipt table during downgrade; it may
    # contain compliance records created by an already-running application.

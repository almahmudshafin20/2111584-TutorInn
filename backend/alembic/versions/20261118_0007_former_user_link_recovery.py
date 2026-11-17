"""Create account-deletion retention schema and former-user recovery safeguards."""

from alembic import context, op
import sqlalchemy as sa


revision = "20261118_0007"
down_revision = "20261116_0006"
branch_labels = None
depends_on = None


DELETION_CHECKS = (
    sa.CheckConstraint("account_role IN ('student', 'tutor')", name="account_deletion_account_role_check"),
    sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="account_deletion_status_check"),
    sa.CheckConstraint("requested_option IN ('anonymize', 'complete')", name="account_deletion_requested_option_check"),
    sa.CheckConstraint("final_option IS NULL OR final_option IN ('anonymize', 'complete')", name="account_deletion_final_option_check"),
    sa.CheckConstraint("requested_account_action IN ('delete_account')", name="account_deletion_requested_account_action_check"),
    sa.CheckConstraint("requested_content_action IN ('account_only', 'delete_selected', 'delete_all', 'retain_all')", name="account_deletion_requested_content_action_check"),
    sa.CheckConstraint("requested_visibility IN ('visible', 'hidden')", name="account_deletion_requested_visibility_check"),
    sa.CheckConstraint("final_account_action IS NULL OR final_account_action IN ('delete_account')", name="account_deletion_final_account_action_check"),
    sa.CheckConstraint("final_content_action IS NULL OR final_content_action IN ('account_only', 'delete_selected', 'delete_all', 'retain_all')", name="account_deletion_final_content_action_check"),
    sa.CheckConstraint("final_visibility IS NULL OR final_visibility IN ('visible', 'hidden')", name="account_deletion_final_visibility_check"),
    sa.CheckConstraint("notification_status IN ('not_sent', 'sent', 'not_configured', 'failed')", name="account_deletion_notification_status_check"),
    sa.CheckConstraint("former_user_link_status IN ('not_sent', 'not_required', 'pending', 'sent', 'not_configured', 'failed')", name="account_deletion_former_user_link_status_check"),
)


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
            *DELETION_CHECKS,
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
            sa.CheckConstraint("visibility IN ('visible', 'hidden')", name="retained_content_visibility_check"),
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
            sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="former_user_removal_status_check"),
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
        existing = sa.inspect(op.get_bind()).get_indexes(table)
        has_equivalent = any(
            index.get("column_names") == columns and bool(index.get("unique")) == unique
            for index in existing
        )
        if name not in {index["name"] for index in existing} and (predicate is not None or not has_equivalent):
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
        inspector = sa.inspect(bind)
        current = next((item for item in inspector.get_columns(table) if item["name"] == column), None)
        if current is None:
            continue
        fk = next((item for item in inspector.get_foreign_keys(table)
                   if item.get("constrained_columns") == [column]
                   and item.get("referred_table") == "user_accounts"), None)
        nullable = current.get("nullable", True)
        already_set_null = bool(fk and (fk.get("options") or {}).get("ondelete", "").upper() == "SET NULL")
        if nullable and already_set_null:
            continue
        fk_name = (fk or {}).get("name") or f"fk_{table}_{column}_user_accounts"
        if dialect == "sqlite":
            naming = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
            with op.batch_alter_table(table, recreate="always", naming_convention=naming) as batch:
                if fk is not None:
                    batch.drop_constraint(fk_name, type_="foreignkey")
                if not nullable:
                    batch.alter_column(column, existing_type=current["type"], existing_nullable=False, nullable=True)
                batch.create_foreign_key(
                    fk_name, "user_accounts", [column], ["id"], ondelete="SET NULL",
                )
        else:
            if not nullable:
                op.alter_column(table, column, existing_type=current["type"], existing_nullable=False, nullable=True)
            if not already_set_null:
                if fk is not None and fk.get("name"):
                    op.drop_constraint(fk["name"], table, type_="foreignkey")
                op.create_foreign_key(
                    fk_name, table, "user_accounts", [column], ["id"], ondelete="SET NULL",
                )


def upgrade():
    if context.is_offline_mode():
        if context.get_context().dialect.name == "postgresql":
            for table, column, old_fk in (
                ("personal_learning_tasks", "owner_account_id", "personal_learning_tasks_owner_account_id_fkey"),
                ("learning_groups", "owner_account_id", "learning_groups_owner_account_id_fkey"),
                ("learning_group_members", "student_account_id", "learning_group_members_student_account_id_fkey"),
                ("group_learning_tasks", "created_by_account_id", "group_learning_tasks_created_by_account_id_fkey"),
                ("group_task_assignments", "student_account_id", "group_task_assignments_student_account_id_fkey"),
            ):
                op.alter_column(table, column, existing_type=sa.Integer(), existing_nullable=False, nullable=True)
                op.drop_constraint(old_fk, table, type_="foreignkey")
                op.create_foreign_key(old_fk, table, "user_accounts", [column], ["id"], ondelete="SET NULL")
        op.create_table(
            "account_deletion_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            *DELETION_COLUMNS,
            *DELETION_CHECKS,
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
            sa.CheckConstraint("visibility IN ('visible', 'hidden')", name="retained_content_visibility_check"),
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
            sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="former_user_removal_status_check"),
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
    # Retained-content ownership receipts and verification history are durable
    # privacy records. Leave these tables in place rather than destroying them
    # during an application rollback.
    pass

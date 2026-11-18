"""Persist and protect the designated First Admin identity."""

from alembic import op
import sqlalchemy as sa


revision = "20261118_0009"
down_revision = "20261118_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column("is_first_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    bind = op.get_bind()
    first_admin_id = bind.execute(
        sa.text("SELECT id FROM user_accounts WHERE role = 'admin' ORDER BY id ASC LIMIT 1")
    ).scalar()
    if first_admin_id is not None:
        bind.execute(
            sa.text("UPDATE user_accounts SET is_first_admin = :is_first_admin WHERE id = :account_id")
            .bindparams(is_first_admin=True, account_id=first_admin_id)
        )

    op.create_index(
        "uq_user_accounts_first_admin",
        "user_accounts",
        ["is_first_admin"],
        unique=True,
        sqlite_where=sa.text("is_first_admin = 1"),
        postgresql_where=sa.text("is_first_admin IS TRUE"),
    )
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION tutorinn_protect_first_admin() RETURNS trigger AS $$
            BEGIN
                IF OLD.is_first_admin IS TRUE THEN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'The designated First Admin account cannot be deleted';
                    END IF;
                    IF NEW.is_first_admin IS NOT TRUE OR NEW.role <> 'admin' OR NEW.status <> 'active' THEN
                        RAISE EXCEPTION 'The designated First Admin account cannot be demoted or disabled';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            CREATE TRIGGER trg_protect_first_admin
            BEFORE UPDATE OF is_first_admin, role, status OR DELETE ON user_accounts
            FOR EACH ROW EXECUTE FUNCTION tutorinn_protect_first_admin();
        """)
    elif bind.dialect.name == "sqlite":
        op.execute("""
            CREATE TRIGGER trg_protect_first_admin_update
            BEFORE UPDATE OF is_first_admin, role, status ON user_accounts
            WHEN OLD.is_first_admin = 1
             AND (NEW.is_first_admin <> 1 OR NEW.role <> 'admin' OR NEW.status <> 'active')
            BEGIN
                SELECT RAISE(ABORT, 'The designated First Admin account cannot be demoted or disabled');
            END;
        """)
        op.execute("""
            CREATE TRIGGER trg_protect_first_admin_delete
            BEFORE DELETE ON user_accounts
            WHEN OLD.is_first_admin = 1
            BEGIN
                SELECT RAISE(ABORT, 'The designated First Admin account cannot be deleted');
            END;
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_protect_first_admin ON user_accounts")
        op.execute("DROP FUNCTION IF EXISTS tutorinn_protect_first_admin()")
    elif bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_protect_first_admin_update")
        op.execute("DROP TRIGGER IF EXISTS trg_protect_first_admin_delete")
    op.drop_index("uq_user_accounts_first_admin", table_name="user_accounts")
    op.drop_column("user_accounts", "is_first_admin")

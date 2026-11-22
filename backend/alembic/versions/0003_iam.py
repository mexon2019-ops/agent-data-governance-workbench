"""Add identity and access-control tables.

Revision ID: 0003_iam
Revises: 0002_audit_logs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_iam"
down_revision = "0002_audit_logs"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(60), nullable=False, unique=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_roles_code", "roles", ["code"], unique=True)
    if not inspector.has_table("permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(100), nullable=False, unique=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("resource", sa.String(100), nullable=False),
            sa.Column("action", sa.String(40), nullable=False),
        )
        op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    if not inspector.has_table("role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        )
        op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
        op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])
    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(80), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(120), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_role_id", "users", ["role_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for table, indexes in [
        ("users", ["ix_users_role_id", "ix_users_username"]),
        ("role_permissions", ["ix_role_permissions_permission_id", "ix_role_permissions_role_id"]),
        ("permissions", ["ix_permissions_code"]),
        ("roles", ["ix_roles_code"]),
    ]:
        if inspector.has_table(table):
            current = {idx["name"] for idx in inspect(bind).get_indexes(table)}
            for name in indexes:
                if name in current:
                    op.drop_index(name, table_name=table)
            op.drop_table(table)

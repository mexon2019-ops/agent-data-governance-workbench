"""Create users, roles and permissions.

Revision ID: 0003_auth_rbac
Revises: 0002_audit_logs
"""
from alembic import op
from app.main import Base

revision = "0003_auth_rbac"
down_revision = "0002_audit_logs"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    names = ["roles", "permissions", "users", "user_roles", "role_permissions"]
    Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[name] for name in names])


def downgrade():
    bind = op.get_bind()
    names = ["role_permissions", "user_roles", "users", "permissions", "roles"]
    Base.metadata.drop_all(bind=bind, tables=[Base.metadata.tables[name] for name in names])

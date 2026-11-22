"""Add API mutation audit log.

Revision ID: 0002_audit_logs
Revises: 0001_baseline
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_audit_logs"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    # The historical baseline imports current SQLAlchemy metadata dynamically.
    # On a fresh database it may already have created this table; on a stamped
    # existing database the table may be absent. Make this revision safe in both cases.
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("request_id", sa.String(length=36), nullable=False),
            sa.Column("actor", sa.String(length=120), nullable=False),
            sa.Column("action", sa.String(length=20), nullable=False),
            sa.Column("resource", sa.String(length=255), nullable=False),
            sa.Column("http_method", sa.String(length=10), nullable=False),
            sa.Column("path", sa.String(length=500), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    existing_indexes = {idx["name"] for idx in inspect(bind).get_indexes("audit_logs")}
    for name, column in [
        ("ix_audit_logs_request_id", "request_id"),
        ("ix_audit_logs_actor", "actor"),
        ("ix_audit_logs_action", "action"),
        ("ix_audit_logs_created_at", "created_at"),
    ]:
        if name not in existing_indexes:
            op.create_index(name, "audit_logs", [column])


def downgrade():
    if inspect(op.get_bind()).has_table("audit_logs"):
        for name in [
            "ix_audit_logs_created_at",
            "ix_audit_logs_action",
            "ix_audit_logs_actor",
            "ix_audit_logs_request_id",
        ]:
            if name in {idx["name"] for idx in inspect(op.get_bind()).get_indexes("audit_logs")}:
                op.drop_index(name, table_name="audit_logs")
        op.drop_table("audit_logs")

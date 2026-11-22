"""Add field-level sensitivity classification.

Revision ID: 0008_field_classification
Revises: 0007_governance_issues
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008_field_classification"
down_revision = "0007_governance_issues"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("metadata_columns"):
        return
    existing = {item["name"] for item in inspector.get_columns("metadata_columns")}
    additions = [
        sa.Column("sensitivity_level", sa.String(length=30), nullable=False, server_default="未分级"),
        sa.Column("classification_basis", sa.Text(), nullable=False, server_default=""),
        sa.Column("classified_by", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("classified_at", sa.DateTime(), nullable=True),
    ]
    for column in additions:
        if column.name not in existing:
            op.add_column("metadata_columns", column)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("metadata_columns"):
        return
    existing = {item["name"] for item in inspector.get_columns("metadata_columns")}
    for name in ["classified_at", "classified_by", "classification_basis", "sensitivity_level"]:
        if name in existing:
            op.drop_column("metadata_columns", name)

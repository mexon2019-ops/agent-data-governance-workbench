"""Add metadata foreign-key lineage edges.

Revision ID: 0009_metadata_lineage
Revises: 0008_field_classification
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0009_metadata_lineage"
down_revision = "0008_field_classification"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("metadata_lineage"):
        op.create_table(
            "metadata_lineage",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_table_id", sa.Integer(), sa.ForeignKey("metadata_tables.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_column_id", sa.Integer(), sa.ForeignKey("metadata_columns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_schema_name", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("target_table_name", sa.String(length=180), nullable=False),
            sa.Column("target_column_name", sa.String(length=180), nullable=False),
            sa.Column("relation_type", sa.String(length=30), nullable=False, server_default="FOREIGN_KEY"),
            sa.Column("discovery_method", sa.String(length=40), nullable=False, server_default="DATABASE_CONSTRAINT"),
            sa.Column("discovered_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "source_column_id", "target_schema_name", "target_table_name", "target_column_name",
                name="uq_metadata_lineage_edge",
            ),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("metadata_lineage")}
    for name, column in [
        ("ix_metadata_lineage_source_table_id", "source_table_id"),
        ("ix_metadata_lineage_source_column_id", "source_column_id"),
    ]:
        if name not in indexes:
            op.create_index(name, "metadata_lineage", [column])


def downgrade():
    bind = op.get_bind()
    if inspect(bind).has_table("metadata_lineage"):
        indexes = {item["name"] for item in inspect(bind).get_indexes("metadata_lineage")}
        for name in ["ix_metadata_lineage_source_column_id", "ix_metadata_lineage_source_table_id"]:
            if name in indexes:
                op.drop_index(name, table_name="metadata_lineage")
        op.drop_table("metadata_lineage")

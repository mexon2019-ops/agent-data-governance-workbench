"""Add versioned data standards and physical field mappings.

Revision ID: 0005_data_standards
Revises: 0004_data_assets
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_data_standards"
down_revision = "0004_data_assets"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("data_standards"):
        op.create_table(
            "data_standards",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("standard_code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("business_domain", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("owner_department", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("owner", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="草稿"),
            sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("standard_code", name="uq_data_standard_code"),
        )
    inspector = inspect(bind)
    for name, column in [
        ("ix_data_standards_standard_code", "standard_code"),
        ("ix_data_standards_name", "name"),
        ("ix_data_standards_business_domain", "business_domain"),
    ]:
        if name not in {item["name"] for item in inspector.get_indexes("data_standards")}:
            op.create_index(name, "data_standards", [column])

    if not inspect(bind).has_table("data_standard_versions"):
        op.create_table(
            "data_standard_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("standard_id", sa.Integer(), sa.ForeignKey("data_standards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("definition", sa.Text(), nullable=False, server_default=""),
            sa.Column("data_type", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("max_length", sa.Integer(), nullable=True),
            sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("format_rule", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("value_range", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("example", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="草稿"),
            sa.Column("effective_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("standard_id", "version_number", name="uq_standard_version"),
        )
    if "ix_data_standard_versions_standard_id" not in {item["name"] for item in inspect(bind).get_indexes("data_standard_versions")}:
        op.create_index("ix_data_standard_versions_standard_id", "data_standard_versions", ["standard_id"])

    if not inspect(bind).has_table("data_standard_mappings"):
        op.create_table(
            "data_standard_mappings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("version_id", sa.Integer(), sa.ForeignKey("data_standard_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("metadata_column_id", sa.Integer(), sa.ForeignKey("metadata_columns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("mapping_status", sa.String(length=30), nullable=False, server_default="待核验"),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("mapped_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("version_id", "metadata_column_id", name="uq_standard_column_mapping"),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("data_standard_mappings")}
    for name, column in [
        ("ix_data_standard_mappings_version_id", "version_id"),
        ("ix_data_standard_mappings_metadata_column_id", "metadata_column_id"),
    ]:
        if name not in indexes:
            op.create_index(name, "data_standard_mappings", [column])


def downgrade():
    op.drop_index("ix_data_standard_mappings_metadata_column_id", table_name="data_standard_mappings")
    op.drop_index("ix_data_standard_mappings_version_id", table_name="data_standard_mappings")
    op.drop_table("data_standard_mappings")
    op.drop_index("ix_data_standard_versions_standard_id", table_name="data_standard_versions")
    op.drop_table("data_standard_versions")
    op.drop_index("ix_data_standards_business_domain", table_name="data_standards")
    op.drop_index("ix_data_standards_name", table_name="data_standards")
    op.drop_index("ix_data_standards_standard_code", table_name="data_standards")
    op.drop_table("data_standards")

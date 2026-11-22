"""Add governed data asset catalog.

Revision ID: 0004_data_assets
Revises: 0003_auth_rbac
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_data_assets"
down_revision = "0003_auth_rbac"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "data_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("metadata_table_id", sa.Integer(), sa.ForeignKey("metadata_tables.id", ondelete="SET NULL"), nullable=True),
        sa.Column("business_domain", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_department", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("owner", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("sensitivity_level", sa.String(length=30), nullable=False, server_default="未分级"),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False, server_default="待确认"),
        sa.Column("tags", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("asset_code", name="uq_data_asset_code"),
        sa.UniqueConstraint("metadata_table_id", name="uq_data_asset_metadata_table"),
    )
    op.create_index("ix_data_assets_asset_code", "data_assets", ["asset_code"])
    op.create_index("ix_data_assets_name", "data_assets", ["name"])
    op.create_index("ix_data_assets_business_domain", "data_assets", ["business_domain"])


def downgrade():
    op.drop_index("ix_data_assets_business_domain", table_name="data_assets")
    op.drop_index("ix_data_assets_name", table_name="data_assets")
    op.drop_index("ix_data_assets_asset_code", table_name="data_assets")
    op.drop_table("data_assets")

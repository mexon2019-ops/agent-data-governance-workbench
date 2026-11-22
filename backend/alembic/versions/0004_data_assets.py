"""Add governed data asset catalog.

Revision ID: 0004_data_assets
Revises: 0003_auth_rbac
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_data_assets"
down_revision = "0003_auth_rbac"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("data_assets"):
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
    existing_indexes = {item["name"] for item in inspect(bind).get_indexes("data_assets")}
    for name, column in [
        ("ix_data_assets_asset_code", "asset_code"),
        ("ix_data_assets_name", "name"),
        ("ix_data_assets_business_domain", "business_domain"),
    ]:
        if name not in existing_indexes:
            op.create_index(name, "data_assets", [column])


def downgrade():
    op.drop_index("ix_data_assets_business_domain", table_name="data_assets")
    op.drop_index("ix_data_assets_name", table_name="data_assets")
    op.drop_index("ix_data_assets_asset_code", table_name="data_assets")
    op.drop_table("data_assets")

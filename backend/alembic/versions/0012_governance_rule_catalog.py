"""Governance rule catalog.
Revision ID: 0012_governance_rule_catalog
Revises: 0011_unified_governance_findings
"""
from alembic import op
import sqlalchemy as sa
revision="0012_governance_rule_catalog"
down_revision="0011_unified_governance_findings"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("governance_rule_catalog",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("rule_code",sa.String(100),nullable=False),
        sa.Column("name",sa.String(180),nullable=False),
        sa.Column("category",sa.String(40),nullable=False),
        sa.Column("template_key",sa.String(80),nullable=False),
        sa.Column("description",sa.Text(),nullable=False,server_default=""),
        sa.Column("severity",sa.String(20),nullable=False,server_default="中"),
        sa.Column("config_json",sa.Text(),nullable=False,server_default="{}"),
        sa.Column("version",sa.Integer(),nullable=False,server_default="1"),
        sa.Column("enabled",sa.Boolean(),nullable=False,server_default="1"),
        sa.Column("created_by",sa.String(120),nullable=False,server_default=""),
        sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_governance_rule_catalog_rule_code","governance_rule_catalog",["rule_code"],unique=True)
    op.create_index("ix_governance_rule_catalog_category","governance_rule_catalog",["category"])
    op.create_index("ix_governance_rule_catalog_enabled","governance_rule_catalog",["enabled"])
def downgrade():
    op.drop_index("ix_governance_rule_catalog_enabled",table_name="governance_rule_catalog")
    op.drop_index("ix_governance_rule_catalog_category",table_name="governance_rule_catalog")
    op.drop_index("ix_governance_rule_catalog_rule_code",table_name="governance_rule_catalog")
    op.drop_table("governance_rule_catalog")

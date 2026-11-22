"""Add read-only data quality rules and run history.

Revision ID: 0006_quality_rules
Revises: 0005_data_standards
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_quality_rules"
down_revision = "0005_data_standards"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("quality_rules"):
        op.create_table(
            "quality_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rule_code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("metadata_table_id", sa.Integer(), sa.ForeignKey("metadata_tables.id", ondelete="CASCADE"), nullable=False),
            sa.Column("metadata_column_id", sa.Integer(), sa.ForeignKey("metadata_columns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("standard_version_id", sa.Integer(), sa.ForeignKey("data_standard_versions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rule_type", sa.String(length=30), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="中"),
            sa.Column("threshold_rate", sa.Float(), nullable=False, server_default="100"),
            sa.Column("config", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("rule_code", name="uq_quality_rule_code"),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("quality_rules")}
    for name, column in [
        ("ix_quality_rules_rule_code", "rule_code"),
        ("ix_quality_rules_name", "name"),
        ("ix_quality_rules_metadata_table_id", "metadata_table_id"),
        ("ix_quality_rules_metadata_column_id", "metadata_column_id"),
        ("ix_quality_rules_rule_type", "rule_type"),
    ]:
        if name not in indexes:
            op.create_index(name, "quality_rules", [column])

    if not inspect(bind).has_table("quality_runs"):
        op.create_table(
            "quality_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rule_id", sa.Integer(), sa.ForeignKey("quality_rules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="运行中"),
            sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("pass_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("message", sa.Text(), nullable=False, server_default=""),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
        )
    if "ix_quality_runs_rule_id" not in {item["name"] for item in inspect(bind).get_indexes("quality_runs")}:
        op.create_index("ix_quality_runs_rule_id", "quality_runs", ["rule_id"])


def downgrade():
    op.drop_index("ix_quality_runs_rule_id", table_name="quality_runs")
    op.drop_table("quality_runs")
    for name in [
        "ix_quality_rules_rule_type", "ix_quality_rules_metadata_column_id",
        "ix_quality_rules_metadata_table_id", "ix_quality_rules_name", "ix_quality_rules_rule_code",
    ]:
        op.drop_index(name, table_name="quality_rules")
    op.drop_table("quality_rules")

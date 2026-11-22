"""Add governance issue remediation workflow.

Revision ID: 0007_governance_issues
Revises: 0006_quality_rules
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_governance_issues"
down_revision = "0006_quality_rules"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("governance_issues"):
        op.create_table(
            "governance_issues",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("issue_code", sa.String(length=80), nullable=False),
            sa.Column("quality_run_id", sa.Integer(), sa.ForeignKey("quality_runs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rule_id", sa.Integer(), sa.ForeignKey("quality_rules.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="中"),
            sa.Column("owner_department", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("owner", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="待分派"),
            sa.Column("due_date", sa.DateTime(), nullable=True),
            sa.Column("remediation_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("review_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("last_recheck_run_id", sa.Integer(), sa.ForeignKey("quality_runs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("issue_code", name="uq_governance_issue_code"),
            sa.UniqueConstraint("quality_run_id", name="uq_governance_issue_quality_run"),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("governance_issues")}
    for name, column in [
        ("ix_governance_issues_issue_code", "issue_code"),
        ("ix_governance_issues_quality_run_id", "quality_run_id"),
        ("ix_governance_issues_rule_id", "rule_id"),
    ]:
        if name not in indexes:
            op.create_index(name, "governance_issues", [column])


def downgrade():
    op.drop_index("ix_governance_issues_rule_id", table_name="governance_issues")
    op.drop_index("ix_governance_issues_quality_run_id", table_name="governance_issues")
    op.drop_index("ix_governance_issues_issue_code", table_name="governance_issues")
    op.drop_table("governance_issues")

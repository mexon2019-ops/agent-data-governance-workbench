"""Unified governance findings registry.

Revision ID: 0011_unified_governance_findings
Revises: 0010_governance_review_events
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_unified_governance_findings"
down_revision = "0010_governance_review_events"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("governance_findings",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("fingerprint",sa.String(64),nullable=False),
        sa.Column("source_type",sa.String(40),nullable=False),
        sa.Column("source_ref",sa.String(160),nullable=False,server_default=""),
        sa.Column("rule_code",sa.String(100),nullable=False,server_default=""),
        sa.Column("title",sa.String(240),nullable=False),
        sa.Column("description",sa.Text(),nullable=False,server_default=""),
        sa.Column("severity",sa.String(20),nullable=False,server_default="中"),
        sa.Column("owner_department",sa.String(120),nullable=False,server_default=""),
        sa.Column("owner",sa.String(120),nullable=False,server_default=""),
        sa.Column("status",sa.String(30),nullable=False,server_default="待处理"),
        sa.Column("evidence_json",sa.Text(),nullable=False,server_default="{}"),
        sa.Column("task_id",sa.Integer(),sa.ForeignKey("governance_tasks.id",ondelete="SET NULL"),nullable=True),
        sa.Column("first_seen_at",sa.DateTime(),nullable=False),
        sa.Column("last_seen_at",sa.DateTime(),nullable=False),
        sa.Column("resolved_at",sa.DateTime(),nullable=True),
        sa.UniqueConstraint("fingerprint",name="uq_governance_finding_fingerprint"))
    op.create_index("ix_governance_findings_source_type","governance_findings",["source_type"])
    op.create_index("ix_governance_findings_status","governance_findings",["status"])
    op.create_index("ix_governance_findings_rule_code","governance_findings",["rule_code"])
    op.create_table("governance_scan_runs",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("scan_code",sa.String(40),nullable=False,unique=True),
        sa.Column("scope_json",sa.Text(),nullable=False,server_default="{}"),
        sa.Column("status",sa.String(30),nullable=False,server_default="完成"),
        sa.Column("issues_created",sa.Integer(),nullable=False,server_default="0"),
        sa.Column("issues_updated",sa.Integer(),nullable=False,server_default="0"),
        sa.Column("issues_found",sa.Integer(),nullable=False,server_default="0"),
        sa.Column("started_by",sa.String(120),nullable=False,server_default=""),
        sa.Column("started_at",sa.DateTime(),nullable=False),
        sa.Column("finished_at",sa.DateTime(),nullable=True),
        sa.Column("message",sa.Text(),nullable=False,server_default=""))
    op.create_index("ix_governance_scan_runs_started_at","governance_scan_runs",["started_at"])

def downgrade():
    op.drop_index("ix_governance_scan_runs_started_at",table_name="governance_scan_runs")
    op.drop_table("governance_scan_runs")
    for ix in ["ix_governance_findings_rule_code","ix_governance_findings_status","ix_governance_findings_source_type"]:
        op.drop_index(ix,table_name="governance_findings")
    op.drop_table("governance_findings")

"""Add dedicated governance review event history.

Revision ID: 0010_governance_review_events
Revises: 0009_metadata_lineage
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0010_governance_review_events"
down_revision = "0009_metadata_lineage"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("governance_review_events"):
        op.create_table(
            "governance_review_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("task_id", sa.Integer(), sa.ForeignKey("governance_tasks.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reviewer", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("decision", sa.String(length=20), nullable=False),
            sa.Column("comment", sa.Text(), nullable=False, server_default=""),
            sa.Column("legacy_record_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("legacy_record_id", name="uq_review_event_legacy_record"),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("governance_review_events")}
    for name, column in [
        ("ix_governance_review_events_task_id", "task_id"),
        ("ix_governance_review_events_reviewer", "reviewer"),
        ("ix_governance_review_events_created_at", "created_at"),
    ]:
        if name not in indexes:
            op.create_index(name, "governance_review_events", [column])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("governance_review_events"):
        indexes = {item["name"] for item in inspector.get_indexes("governance_review_events")}
        for name in ["ix_governance_review_events_created_at", "ix_governance_review_events_reviewer", "ix_governance_review_events_task_id"]:
            if name in indexes:
                op.drop_index(name, table_name="governance_review_events")
        op.drop_table("governance_review_events")

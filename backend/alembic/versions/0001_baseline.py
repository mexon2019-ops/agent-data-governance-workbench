"""Baseline schema for existing workbench models.

Revision ID: 0001_baseline
Revises:
"""
from alembic import op
from app.main import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Baseline captures the current SQLAlchemy model schema. Future schema changes
    # must be generated as explicit Alembic revisions; do not edit this revision
    # after it has been applied in a shared environment.
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())

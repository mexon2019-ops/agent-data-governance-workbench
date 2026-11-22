"""Baseline schema for existing workbench models.

Revision ID: 0001_baseline
Revises:
"""
from alembic import op
from sqlalchemy import inspect
from app.main import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Baseline captures the current SQLAlchemy model schema. Future schema changes
    # must be generated as explicit Alembic revisions; do not edit this revision
    # after it has been applied in a shared environment.
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())
    managed = set(Base.metadata.tables)
    if existing.intersection(managed) and "alembic_version" not in existing:
        raise RuntimeError(
            "检测到已有工作台业务表但尚无 Alembic 版本记录。为避免错误接管旧数据库，"
            "请先备份并核对表结构，再按 Sprint 0 文档执行受控 stamp；禁止自动覆盖或猜测迁移状态。"
        )
    Base.metadata.create_all(bind=bind)

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())

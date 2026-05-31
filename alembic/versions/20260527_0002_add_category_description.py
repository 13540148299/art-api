"""add category description

Revision ID: 20260527_0002
Revises: 20260515_0001
Create Date: 2026-05-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260527_0002"
down_revision: str | None = "20260515_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为分类表增加描述字段。"""
    op.add_column("categories", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    """回滚分类描述字段。"""
    op.drop_column("categories", "description")

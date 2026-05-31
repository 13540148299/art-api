"""add artwork media fields

Revision ID: 20260528_0003
Revises: 20260527_0002
Create Date: 2026-05-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_0003"
down_revision: str | None = "20260527_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增作品图片/视频展示字段。"""
    op.add_column("artworks", sa.Column("media_type", sa.String(length=20), nullable=True))
    op.add_column("artworks", sa.Column("media_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """回滚作品展示字段。"""
    op.drop_column("artworks", "media_url")
    op.drop_column("artworks", "media_type")

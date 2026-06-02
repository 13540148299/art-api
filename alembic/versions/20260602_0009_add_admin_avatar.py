"""增加管理员头像字段

Revision ID: 20260602_0009
Revises: 20260601_0008
Create Date: 2026-06-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0009"
down_revision: str | None = "20260601_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为后台管理员增加头像地址字段。"""
    op.add_column("admins", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """回滚管理员头像地址字段。"""
    op.drop_column("admins", "avatar_url")

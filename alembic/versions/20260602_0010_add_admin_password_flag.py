"""增加管理员初始密码修改标记

Revision ID: 20260602_0010
Revises: 20260602_0009
Create Date: 2026-06-02 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0010"
down_revision: str | None = "20260602_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为管理员增加是否必须修改初始密码的标记。"""
    op.add_column(
        "admins",
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("admins", "must_change_password", server_default=None)


def downgrade() -> None:
    """回滚管理员初始密码修改标记。"""
    op.drop_column("admins", "must_change_password")

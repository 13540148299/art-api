"""增加小程序用户手机号登录字段

Revision ID: 20260529_0005
Revises: 20260528_0004
Create Date: 2026-05-29 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260529_0005"
down_revision: str | None = "20260528_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """允许手机号登录用户存在，并为手机号增加唯一索引。"""
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
    op.alter_column("users", "openid", existing_type=sa.String(length=100), nullable=True)
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)


def downgrade() -> None:
    """回滚手机号登录字段。"""
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.alter_column("users", "openid", existing_type=sa.String(length=100), nullable=False)
    op.drop_column("users", "phone")

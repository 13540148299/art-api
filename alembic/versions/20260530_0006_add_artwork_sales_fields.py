"""增加作品销售价格和库存字段

Revision ID: 20260530_0006
Revises: 20260529_0005
Create Date: 2026-05-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260530_0006"
down_revision: str | None = "20260529_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为作品补充小程序销售所需的价格和库存。"""
    op.add_column(
        "artworks",
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
    )
    op.add_column(
        "artworks",
        sa.Column("stock_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """回滚作品销售字段。"""
    op.drop_column("artworks", "stock_count")
    op.drop_column("artworks", "price")

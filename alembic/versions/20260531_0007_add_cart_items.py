"""增加小程序购物车明细表

Revision ID: 20260531_0007
Revises: 20260530_0006
Create Date: 2026-05-31 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260531_0007"
down_revision: str | None = "20260530_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建购物车明细表，并限制同一用户同一作品只能存在一条记录。"""
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "artwork_id", name="uq_cart_items_user_artwork"),
    )
    op.create_index(op.f("ix_cart_items_id"), "cart_items", ["id"], unique=False)
    op.create_index(op.f("ix_cart_items_user_id"), "cart_items", ["user_id"], unique=False)
    op.create_index(op.f("ix_cart_items_artwork_id"), "cart_items", ["artwork_id"], unique=False)


def downgrade() -> None:
    """回滚购物车明细表。"""
    op.drop_index(op.f("ix_cart_items_artwork_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_user_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_id"), table_name="cart_items")
    op.drop_table("cart_items")

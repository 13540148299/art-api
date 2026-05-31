"""add artwork likes

Revision ID: 20260528_0004
Revises: 20260528_0003
Create Date: 2026-05-28 16:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_0004"
down_revision: str | None = "20260528_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增作品点赞关系表，避免同一用户重复点赞。"""
    op.create_table(
        "artwork_likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], name=op.f("fk_artwork_likes_artwork_id_artworks")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_artwork_likes_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artwork_likes")),
        sa.UniqueConstraint("user_id", "artwork_id", name="uq_artwork_likes_user_artwork"),
    )
    op.create_index(op.f("ix_artwork_likes_artwork_id"), "artwork_likes", ["artwork_id"], unique=False)
    op.create_index(op.f("ix_artwork_likes_id"), "artwork_likes", ["id"], unique=False)
    op.create_index(op.f("ix_artwork_likes_user_id"), "artwork_likes", ["user_id"], unique=False)


def downgrade() -> None:
    """回滚作品点赞关系表。"""
    op.drop_index(op.f("ix_artwork_likes_user_id"), table_name="artwork_likes")
    op.drop_index(op.f("ix_artwork_likes_id"), table_name="artwork_likes")
    op.drop_index(op.f("ix_artwork_likes_artwork_id"), table_name="artwork_likes")
    op.drop_table("artwork_likes")

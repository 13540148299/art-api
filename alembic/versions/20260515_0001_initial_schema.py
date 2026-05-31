"""创建艺术作品平台初始表结构

Revision ID: 20260515_0001
Revises:
Create Date: 2026-05-15 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260515_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建初始业务表。

    本迁移对应 docs/database-erd.md 中的完整 ERD：
    管理员、用户、艺术家、分类、作品、作品图片、收藏、浏览、展览专题、操作日志。
    """
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admins")),
        sa.UniqueConstraint("username", name=op.f("uq_admins_username")),
    )
    op.create_index(op.f("ix_admins_id"), "admins", ["id"], unique=False)
    op.create_index(op.f("ix_admins_role"), "admins", ["role"], unique=False)
    op.create_index(op.f("ix_admins_status"), "admins", ["status"], unique=False)
    op.create_index(op.f("ix_admins_username"), "admins", ["username"], unique=False)

    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("nationality", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artists")),
    )
    op.create_index(op.f("ix_artists_id"), "artists", ["id"], unique=False)
    op.create_index(op.f("ix_artists_name"), "artists", ["name"], unique=False)
    op.create_index(op.f("ix_artists_status"), "artists", ["status"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], name=op.f("fk_categories_parent_id_categories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)
    op.create_index(op.f("ix_categories_status"), "categories", ["status"], unique=False)

    op.create_table(
        "exhibitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exhibitions")),
    )
    op.create_index(op.f("ix_exhibitions_id"), "exhibitions", ["id"], unique=False)
    op.create_index(op.f("ix_exhibitions_status"), "exhibitions", ["status"], unique=False)
    op.create_index(op.f("ix_exhibitions_title"), "exhibitions", ["title"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("openid", sa.String(length=100), nullable=False),
        sa.Column("nickname", sa.String(length=100), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("openid", name=op.f("uq_users_openid")),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_openid"), "users", ["openid"], unique=False)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)

    op.create_table(
        "artworks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.String(length=200), nullable=True),
        sa.Column("artist_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("material", sa.String(length=100), nullable=True),
        sa.Column("size_text", sa.String(length=100), nullable=True),
        sa.Column("creation_year", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], name=op.f("fk_artworks_artist_id_artists")),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name=op.f("fk_artworks_category_id_categories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artworks")),
    )
    op.create_index(op.f("ix_artworks_artist_id"), "artworks", ["artist_id"], unique=False)
    op.create_index(op.f("ix_artworks_category_id"), "artworks", ["category_id"], unique=False)
    op.create_index(op.f("ix_artworks_id"), "artworks", ["id"], unique=False)
    op.create_index(op.f("ix_artworks_is_featured"), "artworks", ["is_featured"], unique=False)
    op.create_index(op.f("ix_artworks_sort_order"), "artworks", ["sort_order"], unique=False)
    op.create_index(op.f("ix_artworks_status"), "artworks", ["status"], unique=False)
    op.create_index(op.f("ix_artworks_title"), "artworks", ["title"], unique=False)

    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], name=op.f("fk_operation_logs_admin_id_admins")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operation_logs")),
    )
    op.create_index(op.f("ix_operation_logs_action"), "operation_logs", ["action"], unique=False)
    op.create_index(op.f("ix_operation_logs_admin_id"), "operation_logs", ["admin_id"], unique=False)
    op.create_index(op.f("ix_operation_logs_id"), "operation_logs", ["id"], unique=False)
    op.create_index(op.f("ix_operation_logs_resource_id"), "operation_logs", ["resource_id"], unique=False)
    op.create_index(op.f("ix_operation_logs_resource_type"), "operation_logs", ["resource_type"], unique=False)

    op.create_table(
        "artwork_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("thumb_url", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], name=op.f("fk_artwork_images_artwork_id_artworks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artwork_images")),
    )
    op.create_index(op.f("ix_artwork_images_artwork_id"), "artwork_images", ["artwork_id"], unique=False)
    op.create_index(op.f("ix_artwork_images_id"), "artwork_images", ["id"], unique=False)

    op.create_table(
        "artwork_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], name=op.f("fk_artwork_views_artwork_id_artworks")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_artwork_views_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artwork_views")),
    )
    op.create_index(op.f("ix_artwork_views_artwork_id"), "artwork_views", ["artwork_id"], unique=False)
    op.create_index(op.f("ix_artwork_views_id"), "artwork_views", ["id"], unique=False)
    op.create_index(op.f("ix_artwork_views_user_id"), "artwork_views", ["user_id"], unique=False)

    op.create_table(
        "exhibition_artworks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exhibition_id", sa.Integer(), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], name=op.f("fk_exhibition_artworks_artwork_id_artworks")),
        sa.ForeignKeyConstraint(["exhibition_id"], ["exhibitions.id"], name=op.f("fk_exhibition_artworks_exhibition_id_exhibitions")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exhibition_artworks")),
        sa.UniqueConstraint("exhibition_id", "artwork_id", name="uq_exhibition_artworks_pair"),
    )
    op.create_index(op.f("ix_exhibition_artworks_artwork_id"), "exhibition_artworks", ["artwork_id"], unique=False)
    op.create_index(op.f("ix_exhibition_artworks_exhibition_id"), "exhibition_artworks", ["exhibition_id"], unique=False)
    op.create_index(op.f("ix_exhibition_artworks_id"), "exhibition_artworks", ["id"], unique=False)

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], name=op.f("fk_favorites_artwork_id_artworks")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_favorites_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_favorites")),
        sa.UniqueConstraint("user_id", "artwork_id", name="uq_favorites_user_artwork"),
    )
    op.create_index(op.f("ix_favorites_artwork_id"), "favorites", ["artwork_id"], unique=False)
    op.create_index(op.f("ix_favorites_id"), "favorites", ["id"], unique=False)
    op.create_index(op.f("ix_favorites_user_id"), "favorites", ["user_id"], unique=False)


def downgrade() -> None:
    """按依赖关系反向删除表，先删子表，再删父表。"""
    op.drop_index(op.f("ix_favorites_user_id"), table_name="favorites")
    op.drop_index(op.f("ix_favorites_id"), table_name="favorites")
    op.drop_index(op.f("ix_favorites_artwork_id"), table_name="favorites")
    op.drop_table("favorites")

    op.drop_index(op.f("ix_exhibition_artworks_id"), table_name="exhibition_artworks")
    op.drop_index(op.f("ix_exhibition_artworks_exhibition_id"), table_name="exhibition_artworks")
    op.drop_index(op.f("ix_exhibition_artworks_artwork_id"), table_name="exhibition_artworks")
    op.drop_table("exhibition_artworks")

    op.drop_index(op.f("ix_artwork_views_user_id"), table_name="artwork_views")
    op.drop_index(op.f("ix_artwork_views_id"), table_name="artwork_views")
    op.drop_index(op.f("ix_artwork_views_artwork_id"), table_name="artwork_views")
    op.drop_table("artwork_views")

    op.drop_index(op.f("ix_artwork_images_id"), table_name="artwork_images")
    op.drop_index(op.f("ix_artwork_images_artwork_id"), table_name="artwork_images")
    op.drop_table("artwork_images")

    op.drop_index(op.f("ix_operation_logs_resource_type"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_resource_id"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_id"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_admin_id"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_action"), table_name="operation_logs")
    op.drop_table("operation_logs")

    op.drop_index(op.f("ix_artworks_title"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_status"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_sort_order"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_is_featured"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_id"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_category_id"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_artist_id"), table_name="artworks")
    op.drop_table("artworks")

    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_openid"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_exhibitions_title"), table_name="exhibitions")
    op.drop_index(op.f("ix_exhibitions_status"), table_name="exhibitions")
    op.drop_index(op.f("ix_exhibitions_id"), table_name="exhibitions")
    op.drop_table("exhibitions")

    op.drop_index(op.f("ix_categories_status"), table_name="categories")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")

    op.drop_index(op.f("ix_artists_status"), table_name="artists")
    op.drop_index(op.f("ix_artists_name"), table_name="artists")
    op.drop_index(op.f("ix_artists_id"), table_name="artists")
    op.drop_table("artists")

    op.drop_index(op.f("ix_admins_username"), table_name="admins")
    op.drop_index(op.f("ix_admins_status"), table_name="admins")
    op.drop_index(op.f("ix_admins_role"), table_name="admins")
    op.drop_index(op.f("ix_admins_id"), table_name="admins")
    op.drop_table("admins")

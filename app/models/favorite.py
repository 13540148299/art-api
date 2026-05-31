from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Favorite(Base, TimestampMixin):
    """作品收藏表。

    ERD 关系：
    - 多条收藏属于一个用户：favorites.user_id -> users.id。
    - 多条收藏指向一个作品：favorites.artwork_id -> artworks.id。

    `user_id + artwork_id` 有唯一约束，避免同一用户重复收藏同一作品。
    """

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "artwork_id", name="uq_favorites_user_artwork"),)

    # 收藏记录主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 收藏用户 ID。
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # 被收藏作品 ID。
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)

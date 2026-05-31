from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ArtworkLike(Base, TimestampMixin):
    """作品点赞表。
    通过 `user_id + artwork_id` 唯一约束限制每个用户只能点赞同一作品一次，作品表中的 like_count 仅作为列表展示的冗余计数。
    """

    __tablename__ = "artwork_likes"
    __table_args__ = (UniqueConstraint("user_id", "artwork_id", name="uq_artwork_likes_user_artwork"),)

    # 点赞记录主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 点赞用户 ID。
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # 被点赞作品 ID。
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)

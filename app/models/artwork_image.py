from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ArtworkImage(Base, TimestampMixin):
    """作品图片表。

    ERD 关系：
    - 一个作品可以拥有多张图片：artworks.id -> artwork_images.artwork_id。

    封面图保存在 `artworks.cover_url`，详情页多图保存在本表。
    继承 TimestampMixin 后会自动拥有 created_at/updated_at 字段。
    """

    __tablename__ = "artwork_images"

    # 图片记录主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 所属作品 ID。
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)

    # 原图或展示图 URL。
    image_url: Mapped[str] = mapped_column(String(500))

    # 缩略图 URL，列表或详情缩略预览优先使用。
    thumb_url: Mapped[str | None] = mapped_column(String(500))

    # 图片排序，支持后台拖拽调整展示顺序。
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

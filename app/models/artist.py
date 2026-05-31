from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Artist(Base, TimestampMixin):
    """艺术家表。

    ERD 关系：
    - 一个艺术家可以拥有多个作品：artists.id -> artworks.artist_id。
    - 小程序艺术家详情页会读取艺术家基础信息，并继续查询其关联作品。
    """

    __tablename__ = "artists"

    # 艺术家主键，作品表通过 artist_id 关联到这里。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 艺术家姓名，后台和小程序都需要支持按姓名搜索。
    name: Mapped[str] = mapped_column(String(100), index=True)

    # 艺术家头像或肖像图片 URL。
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # 艺术家简介，适合存放履历、创作理念、展览经历等长文本。
    bio: Mapped[str | None] = mapped_column(Text)

    # 出生年份，未知或不展示时允许为空。
    birth_year: Mapped[int | None] = mapped_column(Integer)

    # 国籍或地区，例如 China、France，也可以存中文展示值。
    nationality: Mapped[str | None] = mapped_column(String(100))

    # 艺术家状态：active 正常展示、hidden 隐藏。
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

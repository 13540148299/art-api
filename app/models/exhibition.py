from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Exhibition(Base, TimestampMixin):
    """展览专题表。

    ERD 关系：
    - 一个展览专题可以包含多个作品。
    - 专题与作品通过 exhibition_artworks 中间表形成多对多关系。
    """

    __tablename__ = "exhibitions"

    # 专题主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 专题标题。
    title: Mapped[str] = mapped_column(String(200), index=True)

    # 专题封面图 URL。
    cover_url: Mapped[str | None] = mapped_column(String(500))

    # 专题介绍。
    description: Mapped[str | None] = mapped_column(Text)

    # 专题状态：draft 草稿、published 已发布、offline 已下线。
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)

    # 专题开始时间，可用于小程序展示展期。
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 专题结束时间，可为空表示长期展示。
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

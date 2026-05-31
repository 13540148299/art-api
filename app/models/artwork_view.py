from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ArtworkView(Base, TimestampMixin):
    """作品浏览记录表。

    ERD 关系：
    - 登录用户浏览时关联 users.id。
    - 每条记录都关联一个作品 artworks.id。

    该表用于后续统计访问趋势；作品列表展示的浏览量优先读取 `artworks.view_count`。
    继承 TimestampMixin 后会自动记录每次浏览发生时间。
    """

    __tablename__ = "artwork_views"

    # 浏览记录主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 浏览用户 ID。未登录访问时允许为空。
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    # 被浏览作品 ID。
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)

    # 请求来源 IP，用于基础统计和风控。
    ip: Mapped[str | None] = mapped_column(String(64))

    # 浏览器或小程序 User-Agent，用于排查异常访问。
    user_agent: Mapped[str | None] = mapped_column(String(500))

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """小程序用户表。

    ERD 关系：
    - 一个用户可以收藏多个作品：users.id -> favorites.user_id。
    - 一个用户可以产生多条浏览记录：users.id -> artwork_views.user_id。
    """

    __tablename__ = "users"

    # 用户主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 微信 openid，同一个小程序内唯一；手机号登录用户可能暂未绑定微信。
    openid: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)

    # 手机号，同一个手机号只允许绑定一个小程序用户。
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)

    # 微信昵称或用户自定义昵称。
    nickname: Mapped[str | None] = mapped_column(String(100))

    # 用户头像 URL。
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # 用户状态：active 正常、disabled 禁用。
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

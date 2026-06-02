from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Admin(Base, TimestampMixin):
    """后台管理员表。

    ERD 关系：
    - 一个管理员可以产生多条操作日志：admins.id -> operation_logs.admin_id。

    该表用于后台管理系统登录、权限控制和操作审计。
    """

    __tablename__ = "admins"

    # 管理员主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 登录账号，必须唯一。
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # 管理员头像地址，后台个人资料展示使用。
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # 密码哈希，不能存储明文密码。建议使用 Argon2 或 bcrypt。
    password_hash: Mapped[str] = mapped_column(String(255))

    # 管理员角色，例如 super_admin、operator。
    role: Mapped[str] = mapped_column(String(50), default="operator", index=True)

    # 是否必须修改初始密码；超级管理员初始化普通管理员后置为 true。
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)

    # 账号状态：active 正常、disabled 禁用。
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # 最近登录时间，用于后台安全审计。
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

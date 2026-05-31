from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 统一数据库约束命名规则。
# Alembic 自动生成迁移脚本时会使用这些命名，避免不同开发机生成不一致的约束名。
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    """所有 SQLAlchemy ORM 模型的基类。"""

    metadata = metadata


class TimestampMixin:
    """通用时间字段。

    继承该 Mixin 的表会自动拥有：
    - created_at：创建时间，由数据库默认写入。
    - updated_at：更新时间，记录更新时自动刷新。
    """

    # 记录创建时间，使用数据库服务器时间，避免应用服务器时钟不一致。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # 记录最后更新时间，业务数据变更时自动更新。
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

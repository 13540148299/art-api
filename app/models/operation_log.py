from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OperationLog(Base, TimestampMixin):
    """后台操作日志表。

    ERD 关系：
    - 一个管理员可以产生多条日志：admins.id -> operation_logs.admin_id。

    后台的新增、编辑、删除、上下架等关键操作都应写入该表。
    继承 TimestampMixin 后会自动记录操作发生时间。
    """

    __tablename__ = "operation_logs"

    # 日志主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 操作管理员 ID。
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), index=True)

    # 操作类型，例如 create_artwork、update_artwork_status。
    action: Mapped[str] = mapped_column(String(100), index=True)

    # 被操作资源类型，例如 artwork、artist、category。
    resource_type: Mapped[str | None] = mapped_column(String(100), index=True)

    # 被操作资源 ID。
    resource_id: Mapped[int | None] = mapped_column(index=True)

    # 操作来源 IP。
    ip: Mapped[str | None] = mapped_column(String(64))

    # 操作来源 User-Agent。
    user_agent: Mapped[str | None] = mapped_column(String(500))

    # 操作详情，保存变更前后字段等结构化信息。
    detail: Mapped[dict | None] = mapped_column(JSONB)

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """作品分类表。

    ERD 关系：
    - 一个分类可以包含多个作品：categories.id -> artworks.category_id。
    - parent_id 指向自身，可以支持一级/二级分类树。
    """

    __tablename__ = "categories"

    # 分类主键，作品表通过 category_id 关联到这里。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 分类名称，例如油画、雕塑、摄影、综合材料。
    name: Mapped[str] = mapped_column(String(100), index=True)

    # 分类描述，用于后台维护分类说明，也可供前台展示分类介绍。
    description: Mapped[str | None] = mapped_column(Text)

    # 父分类 ID。为空表示一级分类；不为空表示子分类。
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)

    # 分类排序权重，用于后台分类排序和小程序分类列表展示。
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 分类状态：active 正常启用、hidden 隐藏。
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

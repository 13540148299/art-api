from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Artwork(Base, TimestampMixin):
    """艺术作品表。

    ERD 关系：
    - 多个作品属于一个艺术家：artworks.artist_id -> artists.id。
    - 多个作品属于一个分类：artworks.category_id -> categories.id。
    - 一个作品后续可以关联多张作品图片、收藏记录、浏览记录和展览专题。

    这张表是小程序展示和后台上传管理的核心业务表。
    """

    __tablename__ = "artworks"

    # 作品主键，所有作品详情、编辑、上下架接口都通过该 ID 定位作品。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 作品标题，用于小程序列表、详情页和后台搜索。
    title: Mapped[str] = mapped_column(String(200), index=True)

    # 作品副标题，可用于系列名、英文名或短说明。
    subtitle: Mapped[str | None] = mapped_column(String(200))

    # 关联艺术家 ID。当前允许为空，方便先保存草稿，再补全艺术家信息。
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id"), index=True)

    # 关联分类 ID，例如油画、装置、摄影等。
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)

    # 封面图 URL，列表页优先展示该图片。
    cover_url: Mapped[str | None] = mapped_column(String(500))

    # 作品展示资源类型：image 图片、video 视频。未配置时按图片处理，兼容历史数据。
    media_type: Mapped[str | None] = mapped_column(String(20), default="image")

    # 作品展示资源 URL，可保存图片或视频地址；为空时回退到 cover_url。
    media_url: Mapped[str | None] = mapped_column(String(500))

    # 作品介绍，支持较长文本。后续如支持富文本，需要增加 XSS 过滤。
    description: Mapped[str | None] = mapped_column(Text)

    # 作品材质，例如 Oil on canvas、纸本水墨、综合材料等。
    material: Mapped[str | None] = mapped_column(String(100))

    # 作品尺寸，使用文本保存可以兼容“80 x 120 cm”等非结构化表达。
    size_text: Mapped[str | None] = mapped_column(String(100))

    # 作品销售价格，单位为元；未开启销售时保持 0，避免小程序展示空价格。
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # 作品销售库存，小程序加入购物车和后续下单校验优先读取该字段。
    stock_count: Mapped[int] = mapped_column(Integer, default=0)

    # 创作年份，年份未知时允许为空。
    creation_year: Mapped[int | None] = mapped_column(Integer)

    # 作品状态：draft 草稿、published 已上架、offline 已下架。
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)

    # 是否首页推荐，小程序首页优先读取该字段为 True 的作品。
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # 排序权重，数值越大或越小的排序规则由查询层统一约定。
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # 浏览量冗余计数字段，避免每次列表查询都统计浏览记录表。
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    # 点赞量冗余计数字段，后续点赞接口需要同步维护。
    like_count: Mapped[int] = mapped_column(Integer, default=0)

    # 发布时间。作品从草稿变为 published 时写入，用于前台按发布时间排序。
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

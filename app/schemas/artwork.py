from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ArtworkDisplayType = Literal["image", "video"]
ArtworkStatus = Literal["draft", "published", "offline"]


class ArtworkDetail(BaseModel):
    """作品详情响应。

    该结构用于公开端和后台概览展示，只返回界面需要的字段；作品 ID 仅供前端定位记录使用，不作为可见列展示。
    """

    # 作品 ID，由数据库生成，前端仅用于 rowKey 或详情跳转。
    id: int

    # 作品名称，对应 artworks.title。
    title: str

    # 艺术家 ID，后台编辑回显使用，界面表格不展示。
    artist_id: int | None = None

    # 分类 ID，后台编辑回显使用，界面表格不展示。
    category_id: int | None = None

    # 作品介绍，对应 artworks.description。
    description: str | None = None

    # 艺术家名称，来自 artists.name。
    artist_name: str

    # 所属分类名称，来自 categories.name。
    category_name: str | None = None

    # 封面图地址，兼容历史字段 artworks.cover_url。
    cover_url: str

    # 作品展示资源地址，优先使用 media_url，未配置时回退到 cover_url。
    display_url: str

    # 作品展示资源类型，支持图片或视频。
    display_type: ArtworkDisplayType

    # 作品展示资源原始地址，后台编辑回显使用。
    media_url: str | None = None

    # 作品状态：draft 草稿、published 已上架、offline 已下架。
    status: ArtworkStatus = "draft"

    # 作品材质，对应 artworks.material。
    material: str | None = None

    # 作品销售价格，单位为元，用于小程序作品销售展示。
    price: Decimal = Decimal("0.00")

    # 作品销售库存，用于小程序加入购物车和后续订单校验。
    stock_count: int = 0

    # 创作年份，对应 artworks.creation_year。
    creation_year: int | None = None

    # 排序权重，数值越小越靠前。
    sort_order: int = 0

    # 点赞数量，列表和详情页展示使用。
    like_count: int = 0


class ArtworkListResponse(BaseModel):
    """作品列表分页响应。"""

    # 当前页作品数组。
    items: list[ArtworkDetail]

    # 当前页码，从 1 开始。
    page: int

    # 每页数量。
    page_size: int

    # 符合查询条件的总记录数。
    total: int


class AdminArtworkCreateRequest(BaseModel):
    """后台创建作品请求。"""

    # 作品名称支持中英文，长度不超过 100。
    title: str = Field(min_length=1, max_length=100)

    # 作品介绍，允许为空。
    description: str | None = None

    # 关联艺术家 ID，允许先保存草稿后补充。
    artist_id: int | None = None

    # 所属分类 ID，允许为空。
    category_id: int | None = None

    # 作品展示资源类型。
    media_type: ArtworkDisplayType = "image"

    # 作品展示资源地址，图片或视频上传后写入。
    media_url: str | None = Field(default=None, max_length=500)

    # 封面图地址，图片作品默认与 media_url 相同。
    cover_url: str | None = Field(default=None, max_length=500)

    # 作品材质。
    material: str | None = Field(default=None, max_length=100)

    # 作品销售价格，单位为元。
    price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)

    # 作品销售库存，不能为负数。
    stock_count: int = Field(default=0, ge=0)

    # 创作年份。
    creation_year: int | None = Field(default=None, ge=0, le=9999)

    # 作品状态。
    status: ArtworkStatus = "draft"

    # 排序权重。
    sort_order: int = 0

    @field_validator("title")
    @classmethod
    def validate_title_not_blank(cls, value: str) -> str:
        """校验作品名称不能只包含空白字符。"""
        if not value.strip():
            raise ValueError("作品名称不能为空")
        return value

    @model_validator(mode="after")
    def normalize_media_cover(self) -> "AdminArtworkCreateRequest":
        """图片作品未单独传封面时，使用展示资源作为封面。"""
        if self.media_type == "image" and not self.cover_url and self.media_url:
            self.cover_url = self.media_url
        return self


class AdminArtworkUpdateRequest(BaseModel):
    """后台更新作品请求。"""

    # 不传表示不修改；传空白会被拒绝。
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    artist_id: int | None = None
    category_id: int | None = None
    media_type: ArtworkDisplayType | None = None
    media_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    material: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock_count: int | None = Field(default=None, ge=0)
    creation_year: int | None = Field(default=None, ge=0, le=9999)
    status: ArtworkStatus | None = None
    sort_order: int | None = None

    @field_validator("title")
    @classmethod
    def validate_title_not_blank(cls, value: str | None) -> str | None:
        """校验作品名称不能只包含空白字符。"""
        if value is not None and not value.strip():
            raise ValueError("作品名称不能为空")
        return value

    @model_validator(mode="after")
    def validate_not_empty(self) -> "AdminArtworkUpdateRequest":
        """确保 PATCH 请求至少包含一个可更新字段。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        return self


class AdminArtworkDeleteResponse(BaseModel):
    """后台删除作品响应。"""

    # 被删除的作品 ID。
    id: int

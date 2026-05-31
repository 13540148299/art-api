from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ArtistStatus = Literal["active", "hidden"]


class AdminArtistItem(BaseModel):
    """后台艺术家条目响应。"""

    # 艺术家 ID，对应 artists.id。
    id: int

    # 艺术家姓名。
    name: str

    # 艺术家头像或肖像图片 URL。
    avatar_url: str | None = None

    # 艺术家简介、履历或创作理念。
    bio: str | None = None

    # 出生年份，未知时为空。
    birth_year: int | None = None

    # 国籍或地区。
    nationality: str | None = None

    # 艺术家状态：active 展示、hidden 隐藏。
    status: ArtistStatus


class AdminArtistListResponse(BaseModel):
    """后台艺术家列表响应。"""

    # 艺术家列表。
    items: list[AdminArtistItem]

    # 符合筛选条件的艺术家总数。
    total: int


class AdminArtistCreateRequest(BaseModel):
    """后台创建艺术家请求。"""

    # 艺术家姓名，前后空格会在接口层裁剪。
    name: str = Field(min_length=1, max_length=100)

    # 艺术家头像或肖像图片 URL。
    avatar_url: str | None = Field(default=None, max_length=500)

    # 艺术家简介、履历或创作理念。
    bio: str | None = None

    # 出生年份，未知时可不传。
    birth_year: int | None = None

    # 国籍或地区。
    nationality: str | None = Field(default=None, max_length=100)

    # 艺术家状态，默认展示。
    status: ArtistStatus = "active"

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        """校验艺术家姓名不能只包含空白字符。"""
        if not value.strip():
            raise ValueError("艺术家姓名不能为空")
        return value


class AdminArtistUpdateRequest(BaseModel):
    """后台更新艺术家请求。"""

    # 艺术家姓名，不传表示不修改。
    name: str | None = Field(default=None, min_length=1, max_length=100)

    # 艺术家头像或肖像图片 URL，不传表示不修改；传 null 表示清空。
    avatar_url: str | None = Field(default=None, max_length=500)

    # 艺术家简介，不传表示不修改；传 null 表示清空。
    bio: str | None = None

    # 出生年份，不传表示不修改；传 null 表示清空。
    birth_year: int | None = None

    # 国籍或地区，不传表示不修改；传 null 表示清空。
    nationality: str | None = Field(default=None, max_length=100)

    # 艺术家状态，不传表示不修改。
    status: ArtistStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str | None) -> str | None:
        """校验艺术家姓名不能只包含空白字符。"""
        if value is not None and not value.strip():
            raise ValueError("艺术家姓名不能为空")
        return value

    @model_validator(mode="after")
    def validate_not_empty(self) -> "AdminArtistUpdateRequest":
        """确保 PATCH 请求至少包含一个可更新字段。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        return self


class AdminArtistDeleteResponse(BaseModel):
    """后台删除艺术家响应。"""

    # 被删除的艺术家 ID。
    id: int

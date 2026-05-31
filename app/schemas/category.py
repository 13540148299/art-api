from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CategoryStatus = Literal["active", "hidden"]


class CategoryNode(BaseModel):
    """小程序作品分类节点响应。

    分类支持父子层级，前端可以直接使用 children 渲染分类树或二级筛选栏。
    """

    # 分类 ID，对应 categories.id。
    id: int

    # 分类名称，例如油画、雕塑、摄影。
    name: str

    # 分类描述，用于展示分类说明。
    description: str | None = None

    # 父分类 ID。一级分类为空，二级分类为所属父级 ID。
    parent_id: int | None = None

    # 排序权重，数值越小越靠前。
    sort_order: int

    # 子分类列表。没有子分类时返回空数组，方便前端统一处理。
    children: list["CategoryNode"] = Field(default_factory=list)


class CategoryListResponse(BaseModel):
    """作品分类树列表响应。"""

    # 已启用分类树。
    items: list[CategoryNode]


class AdminCategoryItem(BaseModel):
    """后台分类条目响应。"""

    # 分类 ID，对应 categories.id。
    id: int

    # 分类名称。
    name: str

    # 分类描述，便于后台维护分类说明。
    description: str | None = None

    # 父分类 ID，一级分类为空。
    parent_id: int | None = None

    # 排序权重，数值越小越靠前。
    sort_order: int

    # 分类状态：active 启用、hidden 隐藏。
    status: CategoryStatus


class AdminCategoryListResponse(BaseModel):
    """后台分类列表响应。"""

    # 后台分类列表，包含启用和隐藏分类。
    items: list[AdminCategoryItem]

    # 符合筛选条件的分类总数。
    total: int


class AdminCategoryCreateRequest(BaseModel):
    """后台创建分类请求。"""

    # 分类名称，前后空格会在接口层裁剪。
    name: str = Field(min_length=1, max_length=100)

    # 分类描述，可填写分类含义、适用范围或展示文案。
    description: str | None = None

    # 父分类 ID，为空表示创建一级分类。
    parent_id: int | None = None

    # 排序权重，数值越小越靠前。
    sort_order: int = 0

    # 分类状态，默认启用。
    status: CategoryStatus = "active"

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        """校验分类名称不能只包含空白字符。"""
        if not value.strip():
            raise ValueError("分类名称不能为空")
        return value


class AdminCategoryUpdateRequest(BaseModel):
    """后台更新分类请求。"""

    # 分类名称，不传表示不修改。
    name: str | None = Field(default=None, min_length=1, max_length=100)

    # 分类描述，不传表示不修改；传 null 表示清空。
    description: str | None = None

    # 父分类 ID，不传表示不修改；传 null 表示改为一级分类。
    parent_id: int | None = None

    # 排序权重，不传表示不修改。
    sort_order: int | None = None

    # 分类状态，不传表示不修改。
    status: CategoryStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str | None) -> str | None:
        """校验分类名称不能只包含空白字符。"""
        if value is not None and not value.strip():
            raise ValueError("分类名称不能为空")
        return value

    @model_validator(mode="after")
    def validate_not_empty(self) -> "AdminCategoryUpdateRequest":
        """确保 PATCH 请求至少包含一个可更新字段。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        return self


class AdminCategoryDeleteResponse(BaseModel):
    """后台删除分类响应。"""

    # 被删除的分类 ID。
    id: int

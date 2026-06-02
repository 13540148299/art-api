from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

AdminStatus = Literal["active", "disabled"]
AdminRole = Literal["super_admin", "operator"]


class AdminItem(BaseModel):
    """后台管理员列表项。"""

    # 管理员主键。
    id: int

    # 管理员账号名。
    username: str

    # 管理员头像地址。
    avatar_url: str | None = None

    # 管理员角色：super_admin 超级管理员、operator 普通管理员。
    role: AdminRole

    # 账号状态：active 正常、disabled 禁用。
    status: AdminStatus

    # 是否必须修改初始化密码。
    must_change_password: bool


class AdminListResponse(BaseModel):
    """后台管理员列表响应。"""

    # 当前管理员列表。
    items: list[AdminItem]

    # 管理员总数。
    total: int


class AdminCreateRequest(BaseModel):
    """超级管理员创建普通管理员请求。"""

    # 管理员账号名。
    username: str = Field(min_length=1, max_length=100)

    # 初始化密码，普通管理员首次登录后必须修改。
    password: str = Field(min_length=6, max_length=128)

    # 管理员头像地址。
    avatar_url: str | None = Field(default=None, max_length=500)

    # 账号状态，默认启用。
    status: AdminStatus = "active"

    @field_validator("username")
    @classmethod
    def validate_username_not_blank(cls, value: str) -> str:
        """校验管理员账号不能只包含空白字符。"""
        if not value.strip():
            raise ValueError("管理员账号不能为空")
        return value.strip()


class AdminUpdateRequest(BaseModel):
    """超级管理员更新普通管理员请求。"""

    # 管理员账号名，不传表示不修改。
    username: str | None = Field(default=None, min_length=1, max_length=100)

    # 管理员头像地址，传 null 表示清空头像。
    avatar_url: str | None = Field(default=None, max_length=500)

    # 账号状态，不传表示不修改。
    status: AdminStatus | None = None

    # 重置后的初始化密码；不传表示不重置。
    password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username_not_blank(cls, value: str | None) -> str | None:
        """校验管理员账号不能只包含空白字符。"""
        if value is not None and not value.strip():
            raise ValueError("管理员账号不能为空")
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def validate_not_empty(self) -> "AdminUpdateRequest":
        """确保 PATCH 至少包含一个需要更新的字段。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        return self


class AdminDeleteResponse(BaseModel):
    """删除普通管理员响应。"""

    # 被删除的管理员 ID。
    id: int

from pydantic import BaseModel, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    """后台管理员登录请求。"""

    # 管理员账号，对应 admins.username。
    username: str

    # 管理员明文密码。只在登录请求中短暂出现，服务端必须与 password_hash 比对。
    password: str


class TokenResponse(BaseModel):
    """后台管理员登录成功响应。"""

    # JWT access token，后台前端后续请求放到 Authorization: Bearer <token>。
    access_token: str

    # Token 类型，固定为 bearer。
    token_type: str

    # 当前登录管理员账号名，方便前端展示。
    admin_username: str


class AdminProfileResponse(BaseModel):
    """当前后台管理员信息响应。"""

    # 管理员主键。
    id: int

    # 管理员账号名。
    username: str

    # 管理员头像地址。
    avatar_url: str | None = None

    # 管理员角色，例如 super_admin、operator。
    role: str

    # 账号状态：active 正常、disabled 禁用。
    status: str

    # 是否必须修改初始化密码。
    must_change_password: bool = False


class AdminProfileUpdateRequest(BaseModel):
    """当前后台管理员资料更新请求。"""

    # 管理员账号名，不传表示不修改。
    username: str | None = Field(default=None, min_length=1, max_length=100)

    # 管理员头像地址，传 null 表示清空头像。
    avatar_url: str | None = Field(default=None, max_length=500)

    # 修改密码时必须提供当前密码。
    current_password: str | None = None

    # 新密码不传表示不修改密码。
    new_password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username_not_blank(cls, value: str | None) -> str | None:
        """校验管理员账号不能只包含空白字符。"""
        if value is not None and not value.strip():
            raise ValueError("管理员账号不能为空")
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def validate_payload(self) -> "AdminProfileUpdateRequest":
        """校验更新内容和密码修改字段完整性。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        if self.new_password and not self.current_password:
            raise ValueError("修改密码时必须输入当前密码")
        if self.current_password and not self.new_password:
            raise ValueError("请输入新密码")
        return self

from pydantic import BaseModel


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

    # 管理员角色，例如 super_admin、operator。
    role: str

    # 账号状态：active 正常、disabled 禁用。
    status: str

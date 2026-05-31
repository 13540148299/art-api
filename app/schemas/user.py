from pydantic import BaseModel, Field

from app.schemas.artwork import ArtworkDetail


PHONE_PATTERN = r"^1[3-9]\d{9}$"


class MiniappLoginRequest(BaseModel):
    """小程序微信快捷登录请求。

    当前本地联调阶段使用微信 `uni.login` 返回的 code 生成稳定 openid；正式接入微信服务端换取
    openid 后保持该请求结构不变。
    """

    # 微信登录 code，本地开发可传任意非空字符串。
    code: str = Field(min_length=1, max_length=200)

    # 用户昵称，首次登录或用户授权后用于初始化资料。
    nickname: str | None = Field(default=None, max_length=100)

    # 用户头像地址，允许为空。
    avatar_url: str | None = Field(default=None, max_length=500)


class PhoneCodeSendRequest(BaseModel):
    """手机验证码发送请求。"""

    # 国内手机号格式校验，避免无效号码进入验证码流程。
    phone: str = Field(pattern=PHONE_PATTERN)


class PhoneCodeSendResponse(BaseModel):
    """手机验证码发送响应。"""

    phone: str
    expires_in: int
    cooldown_seconds: int
    debug_code: str | None = None


class PhoneLoginRequest(BaseModel):
    """手机验证码登录请求。"""

    # 国内手机号格式校验，需与发送验证码时的手机号一致。
    phone: str = Field(pattern=PHONE_PATTERN)

    # 6 位数字验证码。
    code: str = Field(pattern=r"^\d{6}$")

    # 用户昵称，首次登录时用于初始化资料。
    nickname: str | None = Field(default=None, max_length=100)


class UserProfileUpdateRequest(BaseModel):
    """小程序用户资料更新请求。"""

    # 用户昵称，传空字符串会被拒绝。
    nickname: str | None = Field(default=None, min_length=1, max_length=100)

    # 用户头像地址，传 null 表示清空头像。
    avatar_url: str | None = Field(default=None, max_length=500)


class UserProfileResponse(BaseModel):
    """小程序用户基础资料响应。"""

    id: int
    nickname: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    status: str


class MiniappTokenResponse(BaseModel):
    """小程序登录成功响应。"""

    access_token: str
    token_type: str
    user: UserProfileResponse


class ArtworkInteractionResponse(BaseModel):
    """用户与作品的互动状态。"""

    artwork_id: int
    is_favorited: bool
    is_liked: bool
    like_count: int


class FavoriteListResponse(BaseModel):
    """用户收藏作品列表响应。"""

    items: list[ArtworkDetail]
    total: int

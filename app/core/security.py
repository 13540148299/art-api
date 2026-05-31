from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

password_hasher = PasswordHasher()


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码与 Argon2 密码哈希是否匹配。

    登录场景只返回布尔值，避免把哈希格式错误、密码错误等细节暴露给客户端。
    """
    try:
        return password_hasher.verify(password_hash, plain_password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def get_password_hash(plain_password: str) -> str:
    """生成管理员密码哈希，供初始化管理员或测试数据使用。"""
    return password_hasher.hash(plain_password)


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    """生成后台管理员 access token。

    `sub` 使用稳定的管理员 ID，额外信息放在 claims 中，便于后续鉴权中间件解析角色。
    """
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": expires_at,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """解析并校验后台管理员 access token。

    这里只负责验证签名、过期时间和 token 类型，管理员是否存在、是否禁用由上层鉴权依赖结合数据库判断。
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("无效或已过期的登录凭证") from exc

    if payload.get("type") != "access":
        raise ValueError("登录凭证类型不正确")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("登录凭证缺少管理员身份")

    return payload

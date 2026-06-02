from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.admin import Admin
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login", auto_error=False)


def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    """获取当前已登录后台管理员。

    后台管理接口统一依赖该方法完成 JWT 解析、管理员加载和账号状态校验，避免各接口重复处理鉴权细节。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录凭证无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        if payload.get("subject_type") == "miniapp_user":
            raise ValueError("用户端凭证不能访问后台接口")
        admin_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise credentials_exception from None

    admin = db.execute(select(Admin).where(Admin.id == admin_id)).scalar_one_or_none()
    if admin is None:
        raise credentials_exception

    if admin.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员账号已被禁用",
        )

    return admin


def get_current_operable_admin(current_admin: Admin = Depends(get_current_admin)) -> Admin:
    """获取可正常操作后台业务的管理员。

    使用初始化密码登录的管理员必须先修改密码，修改前只允许访问认证和个人资料接口。
    """
    if current_admin.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先修改初始密码后再使用后台功能",
        )
    return current_admin


def get_current_super_admin(current_admin: Admin = Depends(get_current_operable_admin)) -> Admin:
    """获取当前超级管理员，用于管理员账号管理等高权限操作。"""
    if current_admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可以执行该操作",
        )
    return current_admin


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """获取当前已登录小程序用户。
    用户端接口统一依赖该方法完成 JWT 解析、用户加载和账号状态校验，避免各接口重复处理登录态细节。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录凭证无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        if payload.get("subject_type") != "miniapp_user":
            raise ValueError("登录凭证类型不正确")
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise credentials_exception from None

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )

    return user


def get_optional_current_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """尝试获取当前小程序用户。
    公开接口可使用该依赖在未登录时继续返回公开数据，登录后再补充用户收藏、点赞等个性化状态。
    """
    if not token:
        return None
    try:
        return get_current_user(token=token, db=db)
    except HTTPException:
        return None

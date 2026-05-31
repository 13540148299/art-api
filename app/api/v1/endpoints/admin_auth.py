from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.admin import Admin
from app.models.operation_log import OperationLog
from app.schemas.auth import AdminProfileResponse, LoginRequest, TokenResponse
from app.schemas.common import ApiResponse

router = APIRouter()


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    """后台管理员登录接口。

    根据账号查询管理员，校验密码和账号状态，成功后签发 JWT 并记录登录审计信息。
    """
    admin = db.execute(select(Admin).where(Admin.username == payload.username)).scalar_one_or_none()
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if admin.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员账号已被禁用",
        )

    access_token = create_access_token(
        subject=str(admin.id),
        claims={
            "subject_type": "admin",
            "admin_id": admin.id,
            "username": admin.username,
            "role": admin.role,
        },
    )

    admin.last_login_at = datetime.now(UTC)
    db.add(
        OperationLog(
            admin_id=admin.id,
            action="admin_login",
            resource_type="admin",
            resource_id=admin.id,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detail={"username": admin.username},
        )
    )
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录状态保存失败，请稍后重试",
        ) from exc

    return ApiResponse(
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            admin_username=admin.username,
        )
    )


@router.get("/me", response_model=ApiResponse[AdminProfileResponse])
def get_me(current_admin: Admin = Depends(get_current_admin)) -> ApiResponse[AdminProfileResponse]:
    """查询当前登录管理员信息。

    该接口用于后台前端刷新页面后校验 JWT 是否仍然有效，并获取当前管理员的基础身份信息。
    """
    return ApiResponse(
        data=AdminProfileResponse(
            id=current_admin.id,
            username=current_admin.username,
            role=current_admin.role,
            status=current_admin.status,
        )
    )

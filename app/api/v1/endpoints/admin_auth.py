from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.admin import Admin
from app.models.operation_log import OperationLog
from app.schemas.auth import AdminProfileResponse, AdminProfileUpdateRequest, LoginRequest, TokenResponse
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
            avatar_url=current_admin.avatar_url,
            role=current_admin.role,
            status=current_admin.status,
            must_change_password=bool(current_admin.must_change_password),
        )
    )


@router.patch("/me", response_model=ApiResponse[AdminProfileResponse])
def update_me(
    payload: AdminProfileUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminProfileResponse]:
    """更新当前登录管理员资料。

    支持修改头像、账号名和登录密码；修改密码时必须校验当前密码，避免已登录会话被误操作改密。
    """
    if payload.username is not None and payload.username != current_admin.username:
        exists_admin = db.execute(select(Admin).where(Admin.username == payload.username)).scalar_one_or_none()
        if exists_admin is not None and exists_admin.id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="管理员账号已存在")
        current_admin.username = payload.username

    if "avatar_url" in payload.model_fields_set:
        current_admin.avatar_url = payload.avatar_url

    if payload.new_password:
        if not payload.current_password or not verify_password(payload.current_password, current_admin.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
        current_admin.password_hash = get_password_hash(payload.new_password)
        current_admin.must_change_password = False
    elif current_admin.must_change_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先修改初始密码")

    db.add(
        OperationLog(
            admin_id=current_admin.id,
            action="update_admin_profile",
            resource_type="admin",
            resource_id=current_admin.id,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detail={"username": current_admin.username},
        )
    )
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="管理员资料保存失败，请稍后重试",
        ) from exc

    return ApiResponse(
        data=AdminProfileResponse(
            id=current_admin.id,
            username=current_admin.username,
            avatar_url=current_admin.avatar_url,
            role=current_admin.role,
            status=current_admin.status,
            must_change_password=bool(current_admin.must_change_password),
        )
    )

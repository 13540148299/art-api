from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_super_admin
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.admin import Admin
from app.models.operation_log import OperationLog
from app.schemas.admin import (
    AdminCreateRequest,
    AdminDeleteResponse,
    AdminItem,
    AdminListResponse,
    AdminUpdateRequest,
)
from app.schemas.common import ApiResponse

router = APIRouter()


def _to_admin_item(admin: Admin) -> AdminItem:
    """转换管理员响应对象，避免直接暴露密码哈希等敏感字段。"""
    return AdminItem(
        id=admin.id,
        username=admin.username,
        avatar_url=admin.avatar_url,
        role=admin.role,
        status=admin.status,
        must_change_password=bool(admin.must_change_password),
    )


def _get_operator_or_404(db: Session, admin_id: int) -> Admin:
    """查询普通管理员，不存在或不是普通管理员时返回 404。"""
    admin = db.execute(
        select(Admin).where(Admin.id == admin_id, Admin.role == "operator")
    ).scalar_one_or_none()
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="普通管理员不存在")
    return admin


def _ensure_username_available(db: Session, username: str, ignore_admin_id: int | None = None) -> None:
    """校验管理员账号唯一。"""
    admin = db.execute(select(Admin).where(Admin.username == username)).scalar_one_or_none()
    if admin is not None and admin.id != ignore_admin_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="管理员账号已存在")


def _add_operation_log(
    db: Session,
    current_admin: Admin,
    request: Request,
    action: str,
    target_admin: Admin | None,
    detail: dict,
) -> None:
    """记录管理员账号管理操作日志。"""
    db.add(
        OperationLog(
            admin_id=current_admin.id,
            action=action,
            resource_type="admin",
            resource_id=target_admin.id if target_admin else None,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detail=detail,
        )
    )


def _commit_or_500(db: Session, message: str) -> None:
    """提交事务，失败时回滚并返回统一错误。"""
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc


@router.get("", response_model=ApiResponse[AdminListResponse])
def list_admins(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
) -> ApiResponse[AdminListResponse]:
    """超级管理员查询普通管理员列表。"""
    admins = db.execute(
        select(Admin).where(Admin.role == "operator").order_by(Admin.id.asc())
    ).scalars().all()
    return ApiResponse(data=AdminListResponse(items=[_to_admin_item(admin) for admin in admins], total=len(admins)))


@router.post("", response_model=ApiResponse[AdminItem])
def create_admin(
    payload: AdminCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
) -> ApiResponse[AdminItem]:
    """超级管理员创建普通管理员并初始化账号密码。"""
    _ensure_username_available(db, payload.username)
    admin = Admin(
        username=payload.username,
        avatar_url=payload.avatar_url,
        password_hash=get_password_hash(payload.password),
        role="operator",
        status=payload.status,
        must_change_password=True,
    )
    db.add(admin)
    try:
        db.flush()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="管理员创建失败，请稍后重试") from exc

    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="create_operator_admin",
        target_admin=admin,
        detail={"username": admin.username, "status": admin.status},
    )
    _commit_or_500(db, "管理员创建失败，请稍后重试")
    db.refresh(admin)

    return ApiResponse(data=_to_admin_item(admin))


@router.patch("/{admin_id}", response_model=ApiResponse[AdminItem])
def update_admin(
    admin_id: int,
    payload: AdminUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
) -> ApiResponse[AdminItem]:
    """超级管理员编辑普通管理员资料或重置初始化密码。"""
    admin = _get_operator_or_404(db, admin_id)
    before = _to_admin_item(admin).model_dump()
    update_data = payload.model_dump(exclude_unset=True)

    if payload.username is not None and payload.username != admin.username:
        _ensure_username_available(db, payload.username, ignore_admin_id=admin.id)
        admin.username = payload.username
    if "avatar_url" in update_data:
        admin.avatar_url = payload.avatar_url
    if payload.status is not None:
        admin.status = payload.status
    if payload.password:
        admin.password_hash = get_password_hash(payload.password)
        admin.must_change_password = True

    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="update_operator_admin",
        target_admin=admin,
        detail={"before": before, "after": _to_admin_item(admin).model_dump()},
    )
    _commit_or_500(db, "管理员更新失败，请稍后重试")
    db.refresh(admin)

    return ApiResponse(data=_to_admin_item(admin))


@router.delete("/{admin_id}", response_model=ApiResponse[AdminDeleteResponse])
def delete_admin(
    admin_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
) -> ApiResponse[AdminDeleteResponse]:
    """超级管理员删除普通管理员。"""
    admin = _get_operator_or_404(db, admin_id)
    detail = _to_admin_item(admin).model_dump()
    db.delete(admin)
    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="delete_operator_admin",
        target_admin=admin,
        detail=detail,
    )
    _commit_or_500(db, "管理员删除失败，请稍后重试")

    return ApiResponse(data=AdminDeleteResponse(id=admin_id))

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.models.artwork import Artwork
from app.models.category import Category
from app.models.operation_log import OperationLog
from app.schemas.category import (
    AdminCategoryCreateRequest,
    AdminCategoryDeleteResponse,
    AdminCategoryItem,
    AdminCategoryListResponse,
    AdminCategoryUpdateRequest,
    CategoryStatus,
)
from app.schemas.common import ApiResponse

router = APIRouter()


def _to_admin_category_item(category: Category) -> AdminCategoryItem:
    """转换后台分类响应对象，避免接口直接暴露 ORM 实例。"""
    return AdminCategoryItem(
        id=category.id,
        name=category.name,
        description=category.description,
        parent_id=category.parent_id,
        sort_order=category.sort_order,
        status=category.status,
    )


def _get_category_or_404(db: Session, category_id: int) -> Category:
    """按 ID 查询分类，不存在时返回 404。"""
    category = db.execute(select(Category).where(Category.id == category_id)).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    return category


def _ensure_parent_valid(
    db: Session,
    parent_id: int | None,
    category_id: int | None = None,
) -> None:
    """校验父分类存在且不会形成循环引用。"""
    if parent_id is None:
        return

    if category_id is not None and parent_id == category_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父分类不能是自身")

    categories = db.execute(select(Category)).scalars().all()
    category_map = {category.id: category for category in categories}
    if parent_id not in category_map:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父分类不存在")

    current_parent_id = parent_id
    while current_parent_id is not None:
        if category_id is not None and current_parent_id == category_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父分类不能是自身子级")
        current_parent_id = category_map.get(current_parent_id).parent_id


def _has_child_category(db: Session, category_id: int) -> bool:
    """判断分类下是否存在子分类。"""
    return db.execute(
        select(exists().where(Category.parent_id == category_id))
    ).scalar()


def _has_artwork(db: Session, category_id: int) -> bool:
    """判断分类下是否存在关联作品。"""
    return db.execute(
        select(exists().where(Artwork.category_id == category_id))
    ).scalar()


def _snapshot_category(category: Category) -> dict:
    """提取分类关键字段，用于操作日志记录变更前后内容。"""
    return {
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id,
        "sort_order": category.sort_order,
        "status": category.status,
    }


def _add_operation_log(
    db: Session,
    current_admin: Admin,
    request: Request,
    action: str,
    category_id: int | None,
    detail: dict,
) -> None:
    """记录后台分类操作日志。"""
    db.add(
        OperationLog(
            admin_id=current_admin.id,
            action=action,
            resource_type="category",
            resource_id=category_id,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc


@router.get("", response_model=ApiResponse[AdminCategoryListResponse])
def list_admin_categories(
    category_status: CategoryStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminCategoryListResponse]:
    """后台查询分类列表。

    后台管理需要看到启用和隐藏分类，可通过 status 参数筛选。
    """
    statement = select(Category)
    if category_status is not None:
        statement = statement.where(Category.status == category_status)

    categories = (
        db.execute(statement.order_by(Category.sort_order.asc(), Category.id.asc()))
        .scalars()
        .all()
    )
    return ApiResponse(
        data=AdminCategoryListResponse(
            items=[_to_admin_category_item(category) for category in categories],
            total=len(categories),
        )
    )


@router.post("", response_model=ApiResponse[AdminCategoryItem])
def create_admin_category(
    payload: AdminCategoryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminCategoryItem]:
    """后台创建分类。"""
    _ensure_parent_valid(db, payload.parent_id)

    category = Category(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        parent_id=payload.parent_id,
        sort_order=payload.sort_order,
        status=payload.status,
    )
    db.add(category)
    try:
        db.flush()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="分类创建失败，请稍后重试",
        ) from exc

    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="create_category",
        category_id=category.id,
        detail=_snapshot_category(category),
    )
    _commit_or_500(db, "分类创建失败，请稍后重试")
    db.refresh(category)

    return ApiResponse(data=_to_admin_category_item(category))


@router.get("/{category_id}", response_model=ApiResponse[AdminCategoryItem])
def get_admin_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminCategoryItem]:
    """后台查询分类详情。"""
    category = _get_category_or_404(db, category_id)
    return ApiResponse(data=_to_admin_category_item(category))


@router.patch("/{category_id}", response_model=ApiResponse[AdminCategoryItem])
def update_admin_category(
    category_id: int,
    payload: AdminCategoryUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminCategoryItem]:
    """后台更新分类。"""
    category = _get_category_or_404(db, category_id)
    before = _snapshot_category(category)

    update_data = payload.model_dump(exclude_unset=True)
    if "parent_id" in update_data:
        _ensure_parent_valid(db, payload.parent_id, category_id=category.id)
        category.parent_id = payload.parent_id
    if payload.name is not None:
        category.name = payload.name.strip()
    if "description" in update_data:
        category.description = payload.description.strip() if payload.description else None
    if payload.sort_order is not None:
        category.sort_order = payload.sort_order
    if payload.status is not None:
        category.status = payload.status

    after = _snapshot_category(category)
    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="update_category",
        category_id=category.id,
        detail={"before": before, "after": after},
    )
    _commit_or_500(db, "分类更新失败，请稍后重试")
    db.refresh(category)

    return ApiResponse(data=_to_admin_category_item(category))


@router.delete("/{category_id}", response_model=ApiResponse[AdminCategoryDeleteResponse])
def delete_admin_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminCategoryDeleteResponse]:
    """后台删除分类。

    为避免破坏已有作品数据，存在子分类或关联作品时不允许删除。
    """
    category = _get_category_or_404(db, category_id)
    if _has_child_category(db, category.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="分类下存在子分类，不能删除")
    if _has_artwork(db, category.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="分类下存在作品，不能删除")

    detail = _snapshot_category(category)
    db.delete(category)
    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="delete_category",
        category_id=category.id,
        detail=detail,
    )
    _commit_or_500(db, "分类删除失败，请稍后重试")

    return ApiResponse(data=AdminCategoryDeleteResponse(id=category_id))

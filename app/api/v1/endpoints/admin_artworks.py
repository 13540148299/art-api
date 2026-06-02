from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_operable_admin
from app.api.v1.endpoints.artworks import _build_artwork_filters, _to_artwork_detail
from app.db.session import get_db
from app.models.admin import Admin
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.category import Category
from app.models.operation_log import OperationLog
from app.schemas.artwork import (
    AdminArtworkCreateRequest,
    AdminArtworkDeleteResponse,
    AdminArtworkUpdateRequest,
    ArtworkDetail,
    ArtworkListResponse,
)
from app.schemas.common import ApiResponse

router = APIRouter()


def _get_artwork_or_404(db: Session, artwork_id: int) -> Artwork:
    """按 ID 查询作品，不存在时返回 404。"""
    artwork = db.execute(select(Artwork).where(Artwork.id == artwork_id)).scalar_one_or_none()
    if artwork is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作品不存在")
    return artwork


def _ensure_artist_exists(db: Session, artist_id: int | None) -> None:
    """校验艺术家存在，避免作品引用无效作者。"""
    if artist_id is None:
        return
    exists_artist = db.execute(select(Artist.id).where(Artist.id == artist_id)).scalar_one_or_none()
    if exists_artist is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="艺术家不存在")


def _ensure_category_exists(db: Session, category_id: int | None) -> None:
    """校验分类存在，避免作品引用无效分类。"""
    if category_id is None:
        return
    exists_category = db.execute(select(Category.id).where(Category.id == category_id)).scalar_one_or_none()
    if exists_category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="分类不存在")


def _snapshot_artwork(artwork: Artwork) -> dict:
    """提取作品关键字段，用于操作日志记录变更前后内容。"""
    return {
        "title": artwork.title,
        "description": artwork.description,
        "artist_id": artwork.artist_id,
        "category_id": artwork.category_id,
        "cover_url": artwork.cover_url,
        "media_type": artwork.media_type,
        "media_url": artwork.media_url,
        "material": artwork.material,
        "price": str(artwork.price or 0),
        "stock_count": artwork.stock_count,
        "creation_year": artwork.creation_year,
        "status": artwork.status,
        "sort_order": artwork.sort_order,
    }


def _add_operation_log(
    db: Session,
    current_admin: Admin,
    request: Request,
    action: str,
    artwork_id: int | None,
    detail: dict,
) -> None:
    """记录后台作品操作日志。"""
    db.add(
        OperationLog(
            admin_id=current_admin.id,
            action=action,
            resource_type="artwork",
            resource_id=artwork_id,
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


def _apply_publish_time(artwork: Artwork, previous_status: str | None = None) -> None:
    """作品首次上架时写入发布时间，下架或草稿不清空历史发布时间。"""
    if artwork.status == "published" and previous_status != "published" and artwork.published_at is None:
        artwork.published_at = datetime.now(timezone.utc)


def _load_artwork_detail(db: Session, artwork_id: int) -> ArtworkDetail:
    """重新加载作品详情，补齐艺术家和分类展示名称。"""
    row = (
        db.execute(
            select(Artwork, Artist.name, Category.name)
            .outerjoin(Artist, Artwork.artist_id == Artist.id)
            .outerjoin(Category, Artwork.category_id == Category.id)
            .where(Artwork.id == artwork_id)
        )
        .one()
    )
    artwork, artist_name, category_name = row
    return _to_artwork_detail(artwork, artist_name, category_name)


@router.get("", response_model=ApiResponse[ArtworkListResponse])
def list_admin_artworks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=100),
    artist: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=100),
    year: int | None = Query(default=None, ge=0, le=9999),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_operable_admin),
) -> ApiResponse[ArtworkListResponse]:
    """后台分页查询作品概览。

    后台概览不限制作品状态，便于运营人员完整查看草稿、已上架和已下架作品。
    """
    filters = _build_artwork_filters(keyword, artist, category, year)
    base_statement = (
        select(Artwork)
        .outerjoin(Artist, Artwork.artist_id == Artist.id)
        .outerjoin(Category, Artwork.category_id == Category.id)
    )
    for filter_item in filters:
        base_statement = base_statement.where(filter_item)

    total = db.execute(select(func.count()).select_from(base_statement.subquery())).scalar()
    rows = (
        db.execute(
            select(Artwork, Artist.name, Category.name)
            .outerjoin(Artist, Artwork.artist_id == Artist.id)
            .outerjoin(Category, Artwork.category_id == Category.id)
            .where(*filters)
            .order_by(Artwork.sort_order.asc(), Artwork.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return ApiResponse(
        data=ArtworkListResponse(
            items=[
                _to_artwork_detail(artwork, artist_name, category_name)
                for artwork, artist_name, category_name in rows
            ],
            page=page,
            page_size=page_size,
            total=total or 0,
        )
    )


@router.post("", response_model=ApiResponse[ArtworkDetail])
def create_admin_artwork(
    payload: AdminArtworkCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_operable_admin),
) -> ApiResponse[ArtworkDetail]:
    """后台创建作品。"""
    _ensure_artist_exists(db, payload.artist_id)
    _ensure_category_exists(db, payload.category_id)

    artwork = Artwork(
        title=payload.title.strip(),
        subtitle=None,
        description=payload.description.strip() if payload.description else None,
        artist_id=payload.artist_id,
        category_id=payload.category_id,
        cover_url=payload.cover_url or (payload.media_url if payload.media_type == "image" else None),
        media_type=payload.media_type,
        media_url=payload.media_url,
        material=payload.material.strip() if payload.material else None,
        size_text=None,
        price=payload.price,
        stock_count=payload.stock_count,
        creation_year=payload.creation_year,
        status=payload.status,
        is_featured=False,
        sort_order=payload.sort_order,
        view_count=0,
        like_count=0,
    )
    _apply_publish_time(artwork)
    db.add(artwork)
    try:
        db.flush()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作品创建失败，请稍后重试",
        ) from exc

    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="create_artwork",
        artwork_id=artwork.id,
        detail=_snapshot_artwork(artwork),
    )
    _commit_or_500(db, "作品创建失败，请稍后重试")

    return ApiResponse(data=_load_artwork_detail(db, artwork.id))


@router.patch("/{artwork_id}", response_model=ApiResponse[ArtworkDetail])
def update_admin_artwork(
    artwork_id: int,
    payload: AdminArtworkUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_operable_admin),
) -> ApiResponse[ArtworkDetail]:
    """后台更新作品。"""
    artwork = _get_artwork_or_404(db, artwork_id)
    before = _snapshot_artwork(artwork)
    previous_status = artwork.status
    update_data = payload.model_dump(exclude_unset=True)

    if "artist_id" in update_data:
        _ensure_artist_exists(db, payload.artist_id)
        artwork.artist_id = payload.artist_id
    if "category_id" in update_data:
        _ensure_category_exists(db, payload.category_id)
        artwork.category_id = payload.category_id
    if payload.title is not None:
        artwork.title = payload.title.strip()
    if "description" in update_data:
        artwork.description = payload.description.strip() if payload.description else None
    if "media_type" in update_data and payload.media_type is not None:
        artwork.media_type = payload.media_type
    if "media_url" in update_data:
        artwork.media_url = payload.media_url
    if "cover_url" in update_data:
        artwork.cover_url = payload.cover_url
    if "material" in update_data:
        artwork.material = payload.material.strip() if payload.material else None
    if payload.price is not None:
        artwork.price = payload.price
    if payload.stock_count is not None:
        artwork.stock_count = payload.stock_count
    if "creation_year" in update_data:
        artwork.creation_year = payload.creation_year
    if payload.status is not None:
        artwork.status = payload.status
    if payload.sort_order is not None:
        artwork.sort_order = payload.sort_order

    if artwork.media_type == "image" and not artwork.cover_url and artwork.media_url:
        artwork.cover_url = artwork.media_url
    _apply_publish_time(artwork, previous_status=previous_status)

    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="update_artwork",
        artwork_id=artwork.id,
        detail={"before": before, "after": _snapshot_artwork(artwork)},
    )
    _commit_or_500(db, "作品更新失败，请稍后重试")

    return ApiResponse(data=_load_artwork_detail(db, artwork.id))


@router.delete("/{artwork_id}", response_model=ApiResponse[AdminArtworkDeleteResponse])
def delete_admin_artwork(
    artwork_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_operable_admin),
) -> ApiResponse[AdminArtworkDeleteResponse]:
    """后台删除作品。"""
    artwork = _get_artwork_or_404(db, artwork_id)
    detail = _snapshot_artwork(artwork)
    db.delete(artwork)
    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="delete_artwork",
        artwork_id=artwork.id,
        detail=detail,
    )
    _commit_or_500(db, "作品删除失败，请稍后重试")

    return ApiResponse(data=AdminArtworkDeleteResponse(id=artwork_id))


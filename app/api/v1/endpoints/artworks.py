from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.category import Category
from app.schemas.artwork import ArtworkDetail, ArtworkListResponse
from app.schemas.common import ApiResponse

router = APIRouter()

VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v", ".avi")


def _infer_display_type(media_type: str | None, display_url: str) -> str:
    """推断作品展示资源类型，优先使用数据库配置，兼容仅存 URL 的历史数据。"""
    if media_type in {"image", "video"}:
        return media_type
    normalized_url = display_url.lower().split("?")[0]
    return "video" if normalized_url.endswith(VIDEO_EXTENSIONS) else "image"


def _to_artwork_detail(
    artwork: Artwork,
    artist_name: str | None,
    category_name: str | None,
) -> ArtworkDetail:
    """转换作品列表响应对象，避免接口直接暴露 ORM 实例。"""
    display_url = artwork.media_url or artwork.cover_url or ""
    return ArtworkDetail(
        id=artwork.id,
        title=artwork.title,
        artist_id=artwork.artist_id,
        category_id=artwork.category_id,
        description=artwork.description,
        artist_name=artist_name or "-",
        category_name=category_name,
        cover_url=artwork.cover_url or "",
        display_url=display_url,
        display_type=_infer_display_type(artwork.media_type, display_url),
        media_url=artwork.media_url,
        status=artwork.status,
        material=artwork.material,
        price=artwork.price or 0,
        stock_count=artwork.stock_count or 0,
        creation_year=artwork.creation_year,
        sort_order=artwork.sort_order,
        like_count=artwork.like_count or 0,
    )


def _build_artwork_filters(
    keyword: str | None,
    artist: str | None,
    category: str | None,
    year: int | None,
):
    """构造作品概览筛选条件，支持名称、艺术家、分类和年份组合搜索。"""
    filters = []
    if keyword and keyword.strip():
        keyword_pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                Artwork.title.ilike(keyword_pattern),
                Artist.name.ilike(keyword_pattern),
                Category.name.ilike(keyword_pattern),
                cast(Artwork.creation_year, String).ilike(keyword_pattern),
            )
        )
    if artist and artist.strip():
        filters.append(Artist.name.ilike(f"%{artist.strip()}%"))
    if category and category.strip():
        filters.append(Category.name.ilike(f"%{category.strip()}%"))
    if year is not None:
        filters.append(Artwork.creation_year == year)
    return filters


@router.get("", response_model=ApiResponse[ArtworkListResponse])
def list_artworks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=100),
    artist: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=100),
    year: int | None = Query(default=None, ge=0, le=9999),
    db: Session = Depends(get_db),
) -> ApiResponse[ArtworkListResponse]:
    """分页查询作品概览。

    列表接口采用后端分页，前端翻页或搜索时按需加载，避免一次性拉取大量图片或视频资源。
    """
    filters = [Artwork.status == "published", *_build_artwork_filters(keyword, artist, category, year)]
    base_statement = (
        select(Artwork)
        .outerjoin(Artist, Artwork.artist_id == Artist.id)
        .outerjoin(Category, Artwork.category_id == Category.id)
    )
    for filter_item in filters:
        base_statement = base_statement.where(filter_item)

    total = db.execute(
        select(func.count()).select_from(base_statement.subquery())
    ).scalar()

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


@router.get("/{artwork_id}", response_model=ApiResponse[ArtworkDetail])
def get_artwork(
    artwork_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[ArtworkDetail]:
    """查询作品详情。"""
    row = (
        db.execute(
            select(Artwork, Artist.name, Category.name)
            .outerjoin(Artist, Artwork.artist_id == Artist.id)
            .outerjoin(Category, Artwork.category_id == Category.id)
            .where(Artwork.id == artwork_id)
        )
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作品不存在")

    artwork, artist_name, category_name = row
    return ApiResponse(data=_to_artwork_detail(artwork, artist_name, category_name))

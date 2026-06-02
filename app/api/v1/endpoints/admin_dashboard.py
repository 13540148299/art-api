from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_operable_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.category import Category
from app.schemas.artwork import ArtworkDetail
from app.schemas.common import ApiResponse
from app.schemas.dashboard import AdminDashboardResponse

router = APIRouter()


@router.get("", response_model=ApiResponse[AdminDashboardResponse])
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_operable_admin),
) -> ApiResponse[AdminDashboardResponse]:
    """查询后台工作台概览数据。

    工作台只需要轻量统计和少量最近作品，避免进入后台首页时一次性拉取艺术家、分类和作品完整列表。
    """
    public_artwork_count = db.execute(
        select(func.count()).select_from(Artwork).where(Artwork.status == "published")
    ).scalar()
    artist_count = db.execute(select(func.count()).select_from(Artist)).scalar()
    category_count = db.execute(select(func.count()).select_from(Category)).scalar()
    hidden_artist_count = db.execute(
        select(func.count()).select_from(Artist).where(Artist.status == "hidden")
    ).scalar()
    hidden_category_count = db.execute(
        select(func.count()).select_from(Category).where(Category.status == "hidden")
    ).scalar()

    # 最近作品仅展示公开作品，优先按发布时间排序，未设置发布时间时按主键倒序兜底。
    recent_rows = (
        db.execute(
            select(Artwork, Artist.name)
            .outerjoin(Artist, Artwork.artist_id == Artist.id)
            .where(Artwork.status == "published")
            .order_by(Artwork.published_at.desc().nullslast(), Artwork.id.desc())
            .limit(5)
        )
        .all()
    )
    recent_artworks = [
        ArtworkDetail(
            id=artwork.id,
            title=artwork.title,
            artist_name=artist_name or "-",
            category_name=None,
            cover_url=artwork.cover_url or "",
            display_url=artwork.media_url or artwork.cover_url or "",
            display_type=artwork.media_type if artwork.media_type in {"image", "video"} else "image",
            description=artwork.description,
            status=artwork.status,
            material=artwork.material,
            price=artwork.price or 0,
            stock_count=artwork.stock_count or 0,
            creation_year=artwork.creation_year,
        )
        for artwork, artist_name in recent_rows
    ]

    return ApiResponse(
        data=AdminDashboardResponse(
            public_artwork_count=public_artwork_count or 0,
            artist_count=artist_count or 0,
            category_count=category_count or 0,
            hidden_count=(hidden_artist_count or 0) + (hidden_category_count or 0),
            recent_artworks=recent_artworks,
        )
    )


from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.operation_log import OperationLog
from app.schemas.artist import (
    AdminArtistCreateRequest,
    AdminArtistDeleteResponse,
    AdminArtistItem,
    AdminArtistListResponse,
    AdminArtistUpdateRequest,
    ArtistStatus,
)
from app.schemas.common import ApiResponse

router = APIRouter()


def _to_admin_artist_item(artist: Artist) -> AdminArtistItem:
    """转换后台艺术家响应对象，避免接口直接暴露 ORM 实例。"""
    return AdminArtistItem(
        id=artist.id,
        name=artist.name,
        avatar_url=artist.avatar_url,
        bio=artist.bio,
        birth_year=artist.birth_year,
        nationality=artist.nationality,
        status=artist.status,
    )


def _get_artist_or_404(db: Session, artist_id: int) -> Artist:
    """按 ID 查询艺术家，不存在时返回 404。"""
    artist = db.execute(select(Artist).where(Artist.id == artist_id)).scalar_one_or_none()
    if artist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="艺术家不存在")
    return artist


def _has_artwork(db: Session, artist_id: int) -> bool:
    """判断艺术家下是否存在关联作品。"""
    return db.execute(select(exists().where(Artwork.artist_id == artist_id))).scalar()


def _snapshot_artist(artist: Artist) -> dict:
    """提取艺术家关键字段，用于操作日志记录变更前后内容。"""
    return {
        "name": artist.name,
        "avatar_url": artist.avatar_url,
        "bio": artist.bio,
        "birth_year": artist.birth_year,
        "nationality": artist.nationality,
        "status": artist.status,
    }


def _add_operation_log(
    db: Session,
    current_admin: Admin,
    request: Request,
    action: str,
    artist_id: int | None,
    detail: dict,
) -> None:
    """记录后台艺术家操作日志。"""
    db.add(
        OperationLog(
            admin_id=current_admin.id,
            action=action,
            resource_type="artist",
            resource_id=artist_id,
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


@router.get("", response_model=ApiResponse[AdminArtistListResponse])
def list_admin_artists(
    artist_status: ArtistStatus | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminArtistListResponse]:
    """后台查询艺术家列表。

    后台管理需要看到展示和隐藏艺术家，可通过 status、keyword 进行筛选。
    """
    statement = select(Artist)
    if artist_status is not None:
        statement = statement.where(Artist.status == artist_status)
    if keyword:
        statement = statement.where(Artist.name.ilike(f"%{keyword.strip()}%"))

    artists = db.execute(statement.order_by(Artist.id.asc())).scalars().all()
    return ApiResponse(
        data=AdminArtistListResponse(
            items=[_to_admin_artist_item(artist) for artist in artists],
            total=len(artists),
        )
    )


@router.post("", response_model=ApiResponse[AdminArtistItem])
def create_admin_artist(
    payload: AdminArtistCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminArtistItem]:
    """后台创建艺术家。"""
    artist = Artist(
        name=payload.name.strip(),
        avatar_url=payload.avatar_url,
        bio=payload.bio,
        birth_year=payload.birth_year,
        nationality=payload.nationality,
        status=payload.status,
    )
    db.add(artist)
    try:
        db.flush()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="艺术家创建失败，请稍后重试",
        ) from exc

    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="create_artist",
        artist_id=artist.id,
        detail=_snapshot_artist(artist),
    )
    _commit_or_500(db, "艺术家创建失败，请稍后重试")
    db.refresh(artist)

    return ApiResponse(data=_to_admin_artist_item(artist))


@router.get("/{artist_id}", response_model=ApiResponse[AdminArtistItem])
def get_admin_artist(
    artist_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminArtistItem]:
    """后台查询艺术家详情。"""
    artist = _get_artist_or_404(db, artist_id)
    return ApiResponse(data=_to_admin_artist_item(artist))


@router.patch("/{artist_id}", response_model=ApiResponse[AdminArtistItem])
def update_admin_artist(
    artist_id: int,
    payload: AdminArtistUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminArtistItem]:
    """后台更新艺术家。"""
    artist = _get_artist_or_404(db, artist_id)
    before = _snapshot_artist(artist)
    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and payload.name is not None:
        artist.name = payload.name.strip()
    if "avatar_url" in update_data:
        artist.avatar_url = payload.avatar_url
    if "bio" in update_data:
        artist.bio = payload.bio
    if "birth_year" in update_data:
        artist.birth_year = payload.birth_year
    if "nationality" in update_data:
        artist.nationality = payload.nationality
    if "status" in update_data:
        artist.status = payload.status

    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="update_artist",
        artist_id=artist.id,
        detail={"before": before, "after": _snapshot_artist(artist)},
    )
    _commit_or_500(db, "艺术家更新失败，请稍后重试")
    db.refresh(artist)

    return ApiResponse(data=_to_admin_artist_item(artist))


@router.delete("/{artist_id}", response_model=ApiResponse[AdminArtistDeleteResponse])
def delete_admin_artist(
    artist_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> ApiResponse[AdminArtistDeleteResponse]:
    """后台删除艺术家。

    为避免作品失去作者信息，存在关联作品时不允许删除。
    """
    artist = _get_artist_or_404(db, artist_id)
    if _has_artwork(db, artist.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="艺术家下存在作品，不能删除")

    detail = _snapshot_artist(artist)
    db.delete(artist)
    _add_operation_log(
        db=db,
        current_admin=current_admin,
        request=request,
        action="delete_artist",
        artist_id=artist.id,
        detail=detail,
    )
    _commit_or_500(db, "艺术家删除失败，请稍后重试")

    return ApiResponse(data=AdminArtistDeleteResponse(id=artist_id))

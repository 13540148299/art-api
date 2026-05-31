import hashlib
import random
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.artworks import _to_artwork_detail
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.artwork_like import ArtworkLike
from app.models.category import Category
from app.models.favorite import Favorite
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import (
    ArtworkInteractionResponse,
    FavoriteListResponse,
    MiniappLoginRequest,
    MiniappTokenResponse,
    PhoneCodeSendRequest,
    PhoneCodeSendResponse,
    PhoneLoginRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)

router = APIRouter()
PHONE_CODE_EXPIRE_SECONDS = 300
PHONE_CODE_COOLDOWN_SECONDS = 60
_phone_code_cache: dict[str, tuple[str, datetime]] = {}


def _build_dev_openid(code: str) -> str:
    """根据小程序登录 code 生成本地联调 openid。

    正式接入微信时只需要在这里改为调用 jscode2session，其他登录、资料和互动接口可以保持不变。
    """
    digest = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()[:32]
    return f"dev_{digest}"


def _to_user_profile(user: User) -> UserProfileResponse:
    """转换用户资料响应，避免直接暴露 openid。"""
    return UserProfileResponse(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        phone=user.phone,
        status=user.status,
    )


def _issue_token(user: User) -> MiniappTokenResponse:
    """生成小程序用户访问凭证。"""
    access_token = create_access_token(
        subject=str(user.id),
        claims={
            "subject_type": "miniapp_user",
            "user_id": user.id,
        },
    )
    return MiniappTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_to_user_profile(user),
    )


def _ensure_active_user(user: User) -> None:
    """校验用户状态，禁用用户不允许继续登录。"""
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户账号已被禁用")


def _get_published_artwork_or_404(db: Session, artwork_id: int) -> Artwork:
    """获取可公开互动的作品。"""
    artwork = (
        db.execute(
            select(Artwork).where(
                Artwork.id == artwork_id,
                Artwork.status == "published",
            )
        )
        .scalar_one_or_none()
    )
    if artwork is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作品不存在或未上架")
    return artwork


def _commit_or_500(db: Session, message: str) -> None:
    """提交用户端事务，失败时回滚并返回统一错误。"""
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc


def _get_interaction(db: Session, user: User, artwork_id: int) -> ArtworkInteractionResponse:
    """查询当前用户对作品的收藏和点赞状态。"""
    artwork = _get_published_artwork_or_404(db, artwork_id)
    favorite_id = db.execute(
        select(Favorite.id).where(
            Favorite.user_id == user.id,
            Favorite.artwork_id == artwork_id,
        )
    ).scalar_one_or_none()
    like_id = db.execute(
        select(ArtworkLike.id).where(
            ArtworkLike.user_id == user.id,
            ArtworkLike.artwork_id == artwork_id,
        )
    ).scalar_one_or_none()
    return ArtworkInteractionResponse(
        artwork_id=artwork_id,
        is_favorited=favorite_id is not None,
        is_liked=like_id is not None,
        like_count=artwork.like_count or 0,
    )


@router.post("/login", response_model=ApiResponse[MiniappTokenResponse])
@router.post("/login/wechat", response_model=ApiResponse[MiniappTokenResponse])
def login(
    payload: MiniappLoginRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[MiniappTokenResponse]:
    """小程序微信快捷登录。

    本地联调阶段用 code 生成稳定 openid，首次登录自动创建用户；正式微信登录只需替换 openid 获取方式。
    """
    openid = _build_dev_openid(payload.code)
    user = db.execute(select(User).where(User.openid == openid)).scalar_one_or_none()
    if user is None:
        user = User(
            openid=openid,
            nickname=payload.nickname.strip() if payload.nickname else "艺术访客",
            avatar_url=payload.avatar_url,
            status="active",
        )
        db.add(user)
        _commit_or_500(db, "用户登录失败，请稍后重试")
        db.refresh(user)
    else:
        _ensure_active_user(user)
        if payload.nickname:
            user.nickname = payload.nickname.strip()
        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url
        _commit_or_500(db, "用户登录失败，请稍后重试")

    return ApiResponse(data=_issue_token(user))


@router.post("/phone-code", response_model=ApiResponse[PhoneCodeSendResponse])
def send_phone_code(payload: PhoneCodeSendRequest) -> ApiResponse[PhoneCodeSendResponse]:
    """发送手机验证码。

    当前项目尚未接入短信供应商，先使用内存验证码满足联调闭环；生产环境应替换为短信服务商并接入 Redis 限流。
    """
    now = datetime.now(UTC)
    exists_code = _phone_code_cache.get(payload.phone)
    if exists_code and exists_code[1] > now + timedelta(
        seconds=PHONE_CODE_EXPIRE_SECONDS - PHONE_CODE_COOLDOWN_SECONDS
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="验证码发送过于频繁")

    code = f"{random.randint(0, 999999):06d}"
    expires_at = now + timedelta(seconds=PHONE_CODE_EXPIRE_SECONDS)
    _phone_code_cache[payload.phone] = (code, expires_at)
    return ApiResponse(
        data=PhoneCodeSendResponse(
            phone=payload.phone,
            expires_in=PHONE_CODE_EXPIRE_SECONDS,
            cooldown_seconds=PHONE_CODE_COOLDOWN_SECONDS,
            debug_code=code,
        )
    )


@router.post("/login/phone", response_model=ApiResponse[MiniappTokenResponse])
def login_by_phone(
    payload: PhoneLoginRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[MiniappTokenResponse]:
    """手机验证码登录，首次登录自动创建用户。"""
    cached_code = _phone_code_cache.get(payload.phone)
    if not cached_code or cached_code[1] < datetime.now(UTC) or cached_code[0] != payload.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    user = db.execute(select(User).where(User.phone == payload.phone)).scalar_one_or_none()
    if user is None:
        user = User(
            phone=payload.phone,
            nickname=payload.nickname.strip() if payload.nickname else f"用户{payload.phone[-4:]}",
            status="active",
        )
        db.add(user)
        _commit_or_500(db, "用户登录失败，请稍后重试")
        db.refresh(user)
    else:
        _ensure_active_user(user)
        if payload.nickname:
            user.nickname = payload.nickname.strip()
            _commit_or_500(db, "用户登录失败，请稍后重试")

    _phone_code_cache.pop(payload.phone, None)
    return ApiResponse(data=_issue_token(user))


@router.get("/me", response_model=ApiResponse[UserProfileResponse])
def get_me(current_user: User = Depends(get_current_user)) -> ApiResponse[UserProfileResponse]:
    """获取当前小程序用户资料。"""
    return ApiResponse(data=_to_user_profile(current_user))


@router.patch("/me", response_model=ApiResponse[UserProfileResponse])
def update_me(
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserProfileResponse]:
    """维护当前小程序用户资料。"""
    if payload.nickname is not None:
        current_user.nickname = payload.nickname.strip()
    if "avatar_url" in payload.model_fields_set:
        current_user.avatar_url = payload.avatar_url
    _commit_or_500(db, "用户资料保存失败，请稍后重试")
    return ApiResponse(data=_to_user_profile(current_user))


@router.get("/favorites", response_model=ApiResponse[FavoriteListResponse])
def list_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[FavoriteListResponse]:
    """查询当前用户收藏的已上架作品。"""
    rows = (
        db.execute(
            select(Artwork, Artist.name, Category.name)
            .join(Favorite, Favorite.artwork_id == Artwork.id)
            .outerjoin(Artist, Artwork.artist_id == Artist.id)
            .outerjoin(Category, Artwork.category_id == Category.id)
            .where(Favorite.user_id == current_user.id, Artwork.status == "published")
            .order_by(Favorite.created_at.desc())
        )
        .all()
    )
    total = db.execute(
        select(func.count())
        .select_from(Favorite)
        .join(Artwork, Favorite.artwork_id == Artwork.id)
        .where(Favorite.user_id == current_user.id, Artwork.status == "published")
    ).scalar()
    return ApiResponse(
        data=FavoriteListResponse(
            items=[
                _to_artwork_detail(artwork, artist_name, category_name)
                for artwork, artist_name, category_name in rows
            ],
            total=total or 0,
        )
    )


@router.post("/favorites/{artwork_id}", response_model=ApiResponse[ArtworkInteractionResponse])
def add_favorite(
    artwork_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ArtworkInteractionResponse]:
    """收藏作品，重复收藏保持幂等。"""
    _get_published_artwork_or_404(db, artwork_id)
    exists_favorite = db.execute(
        select(Favorite.id).where(
            Favorite.user_id == current_user.id,
            Favorite.artwork_id == artwork_id,
        )
    ).scalar_one_or_none()
    if exists_favorite is None:
        db.add(Favorite(user_id=current_user.id, artwork_id=artwork_id))
        _commit_or_500(db, "收藏失败，请稍后重试")
    return ApiResponse(data=_get_interaction(db, current_user, artwork_id))


@router.delete("/favorites/{artwork_id}", response_model=ApiResponse[ArtworkInteractionResponse])
def remove_favorite(
    artwork_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ArtworkInteractionResponse]:
    """取消收藏作品，未收藏时保持幂等。"""
    _get_published_artwork_or_404(db, artwork_id)
    favorite = db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.artwork_id == artwork_id,
        )
    ).scalar_one_or_none()
    if favorite is not None:
        db.delete(favorite)
        _commit_or_500(db, "取消收藏失败，请稍后重试")
    return ApiResponse(data=_get_interaction(db, current_user, artwork_id))


@router.post("/likes/{artwork_id}", response_model=ApiResponse[ArtworkInteractionResponse])
def add_like(
    artwork_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ArtworkInteractionResponse]:
    """点赞作品，首次点赞时同步维护作品点赞计数。"""
    artwork = _get_published_artwork_or_404(db, artwork_id)
    exists_like = db.execute(
        select(ArtworkLike.id).where(
            ArtworkLike.user_id == current_user.id,
            ArtworkLike.artwork_id == artwork_id,
        )
    ).scalar_one_or_none()
    if exists_like is None:
        db.add(ArtworkLike(user_id=current_user.id, artwork_id=artwork_id))
        artwork.like_count = (artwork.like_count or 0) + 1
        _commit_or_500(db, "点赞失败，请稍后重试")
    return ApiResponse(data=_get_interaction(db, current_user, artwork_id))


@router.delete("/likes/{artwork_id}", response_model=ApiResponse[ArtworkInteractionResponse])
def remove_like(
    artwork_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ArtworkInteractionResponse]:
    """取消点赞作品，存在点赞记录时同步扣减作品点赞计数。"""
    artwork = _get_published_artwork_or_404(db, artwork_id)
    like = db.execute(
        select(ArtworkLike).where(
            ArtworkLike.user_id == current_user.id,
            ArtworkLike.artwork_id == artwork_id,
        )
    ).scalar_one_or_none()
    if like is not None:
        db.delete(like)
        artwork.like_count = max((artwork.like_count or 0) - 1, 0)
        _commit_or_500(db, "取消点赞失败，请稍后重试")
    return ApiResponse(data=_get_interaction(db, current_user, artwork_id))


@router.get("/artworks/{artwork_id}/interaction", response_model=ApiResponse[ArtworkInteractionResponse])
def get_artwork_interaction(
    artwork_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ArtworkInteractionResponse]:
    """查询当前用户对指定作品的收藏、点赞状态。"""
    return ApiResponse(data=_get_interaction(db, current_user, artwork_id))

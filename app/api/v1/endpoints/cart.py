from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.cart_item import CartItem
from app.models.user import User
from app.schemas.cart import CartItemQuantityRequest, CartItemRequest, CartItemResponse, CartResponse
from app.schemas.common import ApiResponse

router = APIRouter()


def _commit_or_500(db: Session, message: str) -> None:
    """提交购物车事务，失败时回滚并返回统一错误。"""
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc


def _get_sale_artwork_or_404(db: Session, artwork_id: int) -> Artwork:
    """获取可购买作品，不存在、未上架或库存不足时返回明确错误。"""
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
    if (artwork.stock_count or 0) <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="作品库存不足")
    return artwork


def _ensure_quantity_in_stock(artwork: Artwork, quantity: int) -> None:
    """校验购物车数量不超过当前作品库存。"""
    if quantity > (artwork.stock_count or 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已达到库存上限")


def _to_cart_response(rows: list[tuple[CartItem, Artwork, str | None]]) -> CartResponse:
    """将购物车查询结果转换为前端需要的金额、库存和展示字段。"""
    items: list[CartItemResponse] = []
    for cart_item, artwork, artist_name in rows:
        price = Decimal(artwork.price or 0)
        subtotal = price * cart_item.quantity
        items.append(
            CartItemResponse(
                artwork_id=artwork.id,
                title=artwork.title,
                artist_name=artist_name or "-",
                cover_url=artwork.cover_url or artwork.media_url,
                price=price,
                stock_count=artwork.stock_count or 0,
                quantity=cart_item.quantity,
                subtotal=subtotal,
            )
        )

    return CartResponse(
        items=items,
        total_quantity=sum(item.quantity for item in items),
        total_amount=sum((item.subtotal for item in items), Decimal("0.00")),
    )


def _load_cart(db: Session, user_id: int) -> CartResponse:
    """加载当前用户购物车，价格和库存始终取作品表实时值。"""
    rows = (
        db.execute(
            select(CartItem, Artwork, Artist.name)
            .join(Artwork, CartItem.artwork_id == Artwork.id)
            .outerjoin(Artist, Artwork.artist_id == Artist.id)
            .where(CartItem.user_id == user_id, Artwork.status == "published")
            .order_by(CartItem.updated_at.desc(), CartItem.id.desc())
        )
        .all()
    )
    return _to_cart_response(rows)


@router.get("", response_model=ApiResponse[CartResponse])
def list_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[CartResponse]:
    """查询当前用户购物车。"""
    return ApiResponse(data=_load_cart(db, current_user.id))


@router.post("", response_model=ApiResponse[CartResponse])
def add_cart_item(
    payload: CartItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[CartResponse]:
    """加入购物车；重复加入同一作品时累加数量。"""
    artwork = _get_sale_artwork_or_404(db, payload.artwork_id)
    cart_item = (
        db.execute(
            select(CartItem).where(
                CartItem.user_id == current_user.id,
                CartItem.artwork_id == payload.artwork_id,
            )
        )
        .scalar_one_or_none()
    )
    next_quantity = payload.quantity if cart_item is None else cart_item.quantity + payload.quantity
    _ensure_quantity_in_stock(artwork, next_quantity)

    if cart_item is None:
        db.add(CartItem(user_id=current_user.id, artwork_id=payload.artwork_id, quantity=payload.quantity))
    else:
        cart_item.quantity = next_quantity
    _commit_or_500(db, "加入购物车失败，请稍后重试")
    return ApiResponse(data=_load_cart(db, current_user.id))


@router.patch("/{artwork_id}", response_model=ApiResponse[CartResponse])
def update_cart_item(
    artwork_id: int,
    payload: CartItemQuantityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[CartResponse]:
    """更新购物车作品数量。"""
    artwork = _get_sale_artwork_or_404(db, artwork_id)
    _ensure_quantity_in_stock(artwork, payload.quantity)
    cart_item = (
        db.execute(
            select(CartItem).where(
                CartItem.user_id == current_user.id,
                CartItem.artwork_id == artwork_id,
            )
        )
        .scalar_one_or_none()
    )
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="购物车中不存在该作品")

    cart_item.quantity = payload.quantity
    _commit_or_500(db, "购物车更新失败，请稍后重试")
    return ApiResponse(data=_load_cart(db, current_user.id))


@router.delete("/{artwork_id}", response_model=ApiResponse[CartResponse])
def remove_cart_item(
    artwork_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[CartResponse]:
    """移除购物车中的指定作品，重复删除保持幂等。"""
    cart_item = (
        db.execute(
            select(CartItem).where(
                CartItem.user_id == current_user.id,
                CartItem.artwork_id == artwork_id,
            )
        )
        .scalar_one_or_none()
    )
    if cart_item is not None:
        db.delete(cart_item)
        _commit_or_500(db, "购物车移除失败，请稍后重试")
    return ApiResponse(data=_load_cart(db, current_user.id))


@router.delete("", response_model=ApiResponse[CartResponse])
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[CartResponse]:
    """清空当前用户购物车。"""
    db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
    _commit_or_500(db, "购物车清空失败，请稍后重试")
    return ApiResponse(data=CartResponse(items=[], total_quantity=0, total_amount=Decimal("0.00")))

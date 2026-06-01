from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.cart_item import CartItem
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.order import OrderCheckoutRequest, OrderItemResponse, OrderListResponse, OrderResponse

router = APIRouter()

ORDER_STATUS_TEXT = {
    "pending_payment": "待付款",
    "paid": "待收货",
    "completed": "已完成",
    "cancelled": "已取消",
}


def _commit_or_500(db: Session, message: str) -> None:
    """提交订单事务，失败时回滚并返回统一错误。"""
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc


def _build_order_no(user_id: int) -> str:
    """生成订单号，包含时间和用户片段，便于客服按时间追踪。"""
    return f"AO{datetime.now():%Y%m%d%H%M%S}{user_id % 10000:04d}{uuid4().hex[:6].upper()}"


def _normalize_text(value: str | None) -> str | None:
    """清理用户输入的首尾空白，空字符串统一按空值处理。"""
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _to_order_response(order: Order, items: list[OrderItem]) -> OrderResponse:
    """转换订单响应，统一补充中文状态文案。"""
    return OrderResponse(
        id=order.id,
        order_no=order.order_no,
        status=order.status,
        status_text=ORDER_STATUS_TEXT.get(order.status, "未知状态"),
        total_amount=order.total_amount,
        total_quantity=order.total_quantity,
        contact_name=order.contact_name,
        contact_phone=order.contact_phone,
        shipping_address=order.shipping_address,
        remark=order.remark,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemResponse(
                id=item.id,
                artwork_id=item.artwork_id,
                title=item.title,
                artist_name=item.artist_name,
                cover_url=item.cover_url,
                price=item.price,
                quantity=item.quantity,
                subtotal=item.subtotal,
            )
            for item in items
        ],
    )


def _load_user_order(db: Session, user_id: int, order_id: int) -> tuple[Order, list[OrderItem]]:
    """加载当前用户订单，避免用户越权查看他人订单。"""
    order = db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    items = (
        db.execute(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id.asc()))
        .scalars()
        .all()
    )
    return order, list(items)


@router.get("", response_model=ApiResponse[OrderListResponse])
def list_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[OrderListResponse]:
    """分页查询当前用户订单。"""
    filters = [Order.user_id == current_user.id]
    if status_filter:
        filters.append(Order.status == status_filter)

    total = db.execute(select(func.count()).select_from(Order).where(*filters)).scalar() or 0
    orders = (
        db.execute(
            select(Order)
            .where(*filters)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    order_ids = [order.id for order in orders]
    rows = (
        db.execute(select(OrderItem).where(OrderItem.order_id.in_(order_ids)).order_by(OrderItem.id.asc()))
        .scalars()
        .all()
        if order_ids
        else []
    )
    items_by_order: dict[int, list[OrderItem]] = {order_id: [] for order_id in order_ids}
    for item in rows:
        items_by_order.setdefault(item.order_id, []).append(item)

    return ApiResponse(
        data=OrderListResponse(
            items=[_to_order_response(order, items_by_order.get(order.id, [])) for order in orders],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.post("/checkout", response_model=ApiResponse[OrderResponse])
def checkout_order(
    payload: OrderCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[OrderResponse]:
    """从当前购物车创建订单，并扣减作品库存。"""
    rows = (
        db.execute(
            select(CartItem, Artwork, Artist.name)
            .join(Artwork, CartItem.artwork_id == Artwork.id)
            .outerjoin(Artist, Artwork.artist_id == Artist.id)
            .where(CartItem.user_id == current_user.id, Artwork.status == "published")
            .order_by(CartItem.id.asc())
        )
        .all()
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="购物车为空，无法创建订单")

    total_amount = Decimal("0.00")
    total_quantity = 0
    order_items: list[OrderItem] = []
    for cart_item, artwork, artist_name in rows:
        if cart_item.quantity > (artwork.stock_count or 0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"作品「{artwork.title}」库存不足")

        price = Decimal(artwork.price or 0)
        subtotal = price * cart_item.quantity
        total_amount += subtotal
        total_quantity += cart_item.quantity
        artwork.stock_count = (artwork.stock_count or 0) - cart_item.quantity
        order_items.append(
            OrderItem(
                artwork_id=artwork.id,
                title=artwork.title,
                artist_name=artist_name or "-",
                cover_url=artwork.cover_url or artwork.media_url,
                price=price,
                quantity=cart_item.quantity,
                subtotal=subtotal,
            )
        )

    order = Order(
        order_no=_build_order_no(current_user.id),
        user_id=current_user.id,
        status="pending_payment",
        total_amount=total_amount,
        total_quantity=total_quantity,
        contact_name=payload.contact_name.strip(),
        contact_phone=payload.contact_phone.strip(),
        shipping_address=payload.shipping_address.strip(),
        remark=_normalize_text(payload.remark),
    )
    db.add(order)
    db.flush()
    for item in order_items:
        item.order_id = order.id
        db.add(item)
    db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
    _commit_or_500(db, "订单创建失败，请稍后重试")

    return ApiResponse(data=_to_order_response(order, order_items))


@router.get("/{order_id}", response_model=ApiResponse[OrderResponse])
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[OrderResponse]:
    """查询当前用户订单详情。"""
    order, items = _load_user_order(db, current_user.id, order_id)
    return ApiResponse(data=_to_order_response(order, items))


@router.patch("/{order_id}/cancel", response_model=ApiResponse[OrderResponse])
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[OrderResponse]:
    """取消待付款订单，并返还已锁定库存。"""
    order, items = _load_user_order(db, current_user.id, order_id)
    if order.status != "pending_payment":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅待付款订单可以取消")

    artworks = (
        db.execute(select(Artwork).where(Artwork.id.in_([item.artwork_id for item in items]))).scalars().all()
        if items
        else []
    )
    artwork_by_id = {artwork.id: artwork for artwork in artworks}
    for item in items:
        artwork = artwork_by_id.get(item.artwork_id)
        if artwork is not None:
            artwork.stock_count = (artwork.stock_count or 0) + item.quantity
    order.status = "cancelled"
    _commit_or_500(db, "订单取消失败，请稍后重试")
    return ApiResponse(data=_to_order_response(order, items))


@router.patch("/{order_id}/pay", response_model=ApiResponse[OrderResponse])
def pay_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[OrderResponse]:
    """本地演示用支付确认接口，真实支付接入后应由支付回调更新状态。"""
    order, items = _load_user_order(db, current_user.id, order_id)
    if order.status != "pending_payment":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅待付款订单可以支付")
    order.status = "paid"
    _commit_or_500(db, "订单支付失败，请稍后重试")
    return ApiResponse(data=_to_order_response(order, items))


@router.patch("/{order_id}/complete", response_model=ApiResponse[OrderResponse])
def complete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[OrderResponse]:
    """确认收货并完成订单。"""
    order, items = _load_user_order(db, current_user.id, order_id)
    if order.status != "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅待收货订单可以确认收货")
    order.status = "completed"
    _commit_or_500(db, "订单确认失败，请稍后重试")
    return ApiResponse(data=_to_order_response(order, items))

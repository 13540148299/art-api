from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Order(Base, TimestampMixin):
    """小程序订单主表。

    订单主表保存用户、金额、状态和收货信息；订单明细会保存作品下单时的快照，
    避免后续作品改名、改价影响历史订单展示。
    """

    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("order_no", name="uq_orders_order_no"),)

    # 订单主键，前端详情页通过该 ID 查询订单。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 对用户展示和客服检索使用的订单号。
    order_no: Mapped[str] = mapped_column(String(32), index=True)

    # 下单用户 ID。
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # 订单状态：pending_payment 待付款、paid 已付款、completed 已完成、cancelled 已取消。
    status: Mapped[str] = mapped_column(String(32), default="pending_payment", index=True)

    # 订单总金额，创建时由订单明细小计汇总。
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # 订单商品总件数。
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # 收货人信息。当前先满足小程序订单闭环，后续可拆出地址簿。
    contact_name: Mapped[str] = mapped_column(String(50))
    contact_phone: Mapped[str] = mapped_column(String(20))
    shipping_address: Mapped[str] = mapped_column(String(300))

    # 用户下单备注。
    remark: Mapped[str | None] = mapped_column(Text)


class OrderItem(Base, TimestampMixin):
    """小程序订单明细表。

    每条明细对应下单时购物车中的一个作品，保存价格、数量和展示信息快照。
    """

    __tablename__ = "order_items"

    # 明细主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 所属订单 ID。
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)

    # 作品 ID，用于从订单详情跳回作品详情。
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)

    # 下单时的作品标题、艺术家和封面快照。
    title: Mapped[str] = mapped_column(String(200))
    artist_name: Mapped[str] = mapped_column(String(100))
    cover_url: Mapped[str | None] = mapped_column(String(500))

    # 下单单价和数量。
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # 明细小计，避免前端重复计算和浮点误差。
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

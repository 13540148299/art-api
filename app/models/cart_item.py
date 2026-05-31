from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CartItem(Base, TimestampMixin):
    """小程序购物车明细表。

    ERD 关系：
    - 一个用户可以拥有多条购物车明细：cart_items.user_id -> users.id。
    - 一条购物车明细对应一个作品：cart_items.artwork_id -> artworks.id。

    `user_id + artwork_id` 唯一约束保证同一作品在同一用户购物车中只出现一次。
    """

    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "artwork_id", name="uq_cart_items_user_artwork"),)

    # 购物车明细主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 购物车所属用户 ID。
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # 加入购物车的作品 ID。
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)

    # 购买数量。接口层会根据作品库存限制该值不能超过可售库存。
    quantity: Mapped[int] = mapped_column(Integer, default=1)

from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemRequest(BaseModel):
    """加入购物车请求。"""

    # 作品 ID，只允许加入已上架作品。
    artwork_id: int

    # 加购数量，接口层会继续按库存做上限校验。
    quantity: int = Field(default=1, ge=1)


class CartItemQuantityRequest(BaseModel):
    """更新购物车数量请求。"""

    # 目标数量，必须大于 0；删除明细请调用删除接口。
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    """购物车明细响应。"""

    artwork_id: int
    title: str
    artist_name: str
    cover_url: str | None = None
    price: Decimal = Decimal("0.00")
    stock_count: int = 0
    quantity: int
    subtotal: Decimal = Decimal("0.00")


class CartResponse(BaseModel):
    """购物车列表响应。"""

    items: list[CartItemResponse]
    total_quantity: int
    total_amount: Decimal = Decimal("0.00")

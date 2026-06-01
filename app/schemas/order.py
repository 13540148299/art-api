from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class OrderCheckoutRequest(BaseModel):
    """购物车结算请求。"""

    # 收货人姓名，当前订单创建必须填写，便于后续客服履约。
    contact_name: str = Field(min_length=1, max_length=50)

    # 收货人手机号，接口层保留字符串以兼容区号、座机等后续场景。
    contact_phone: str = Field(min_length=6, max_length=20)

    # 收货地址，当前先保存完整文本地址。
    shipping_address: str = Field(min_length=1, max_length=300)

    # 用户备注，空字符串会在接口层归一化为 None。
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("contact_name", "contact_phone", "shipping_address")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """校验必填文本不能只包含空白字符。"""
        if not value.strip():
            raise ValueError("必填信息不能为空")
        return value


class OrderItemResponse(BaseModel):
    """订单明细响应。"""

    id: int
    artwork_id: int
    title: str
    artist_name: str
    cover_url: str | None = None
    price: Decimal = Decimal("0.00")
    quantity: int
    subtotal: Decimal = Decimal("0.00")


class OrderResponse(BaseModel):
    """订单详情响应。"""

    id: int
    order_no: str
    status: str
    status_text: str
    total_amount: Decimal = Decimal("0.00")
    total_quantity: int
    contact_name: str
    contact_phone: str
    shipping_address: str
    remark: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]


class OrderListResponse(BaseModel):
    """订单分页列表响应。"""

    items: list[OrderResponse]
    page: int
    page_size: int
    total: int

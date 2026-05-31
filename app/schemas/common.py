from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应结构。

    所有接口都返回相同外层结构，前端可以统一处理成功、失败和业务数据。
    - code：业务状态码，0 表示成功。
    - message：业务提示信息，失败时放错误原因。
    - data：接口实际返回的数据，类型由具体接口决定。
    """

    code: int = 0
    message: str = "ok"
    data: T

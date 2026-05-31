from fastapi import APIRouter

from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    """健康检查接口。

    用途：
    - 本地开发时确认 FastAPI 服务是否已经启动。
    - 生产部署时提供给 Nginx、容器平台或监控系统做存活探测。

    该接口不访问数据库和 Redis，避免外部依赖故障影响服务进程存活判断。
    后续如果需要检查数据库连接，可以新增 `/health/deep` 深度检查接口。
    """
    return ApiResponse(data={"status": "ok"})

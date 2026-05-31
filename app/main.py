from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。

    这里集中完成全局能力装配：注册 CORS、挂载 API 路由，并暴露本地上传文件访问入口。
    """
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        # 允许访问后端的前端域名列表，生产环境必须改成真实域名白名单。
        allow_origins=settings.backend_cors_origins,
        # 允许携带 Authorization 等凭证，后台管理系统登录后会依赖它。
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 所有 v1 API 统一从 app.api.v1.router 聚合，便于后续增加 v2 版本。
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    # 本地上传文件静态访问入口，头像上传后会返回 /uploads/... 形式的访问路径。
    Path("uploads").mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    return app


# ASGI 服务器 uvicorn 默认加载这个 app 对象。
app = create_app()

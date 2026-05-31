from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置对象。

    配置优先从项目根目录 `.env` 文件读取；如果 `.env` 中没有对应值，则使用下面的默认值。
    这样可以保证本地开发、测试环境、生产环境使用同一份代码，只通过环境变量切换配置。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 应用名称，会显示在 FastAPI 自动生成的 Swagger 文档中。
    app_name: str = "Art API"

    # 当前运行环境：local/test/prod，用于后续控制日志级别、调试能力等。
    environment: str = "local"

    # API 版本前缀，当前所有接口统一挂载到 /api/v1。
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL 连接地址。正式环境请使用独立账号和强密码，不要提交真实连接串。
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/art_platform"

    # Redis 连接地址，后续用于缓存、限流、验证码、热门作品等能力。
    redis_url: str = "redis://localhost:6379/0"

    # JWT 签名密钥，生产环境必须改为高强度随机字符串。
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    # 后台管理员 access token 有效期，单位：分钟。
    access_token_expire_minutes: int = 120

    # 允许跨域访问 API 的前端域名列表。`.env` 中需要写成 JSON 数组格式。
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


# 全局单例配置对象，其他模块通过导入 settings 读取配置。
settings = Settings()

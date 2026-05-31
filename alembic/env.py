from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models import *  # noqa: F403
from app.models.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic 自动迁移读取这里的 metadata。
# app.models 的集中导入会确保所有 ORM 表都被注册到 Base.metadata 中。
target_metadata = Base.metadata


def get_database_url() -> str:
    """读取数据库连接串。

    迁移命令优先使用 `.env` 中的 DATABASE_URL，避免 alembic.ini 写死环境配置。
    """
    return settings.database_url


def run_migrations_offline() -> None:
    """离线模式生成 SQL。

    例如执行 `alembic upgrade head --sql` 时会进入这里，不需要真实连接数据库。
    """
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式执行迁移。

    例如执行 `alembic upgrade head` 时会连接 PostgreSQL 并真正创建/修改表结构。
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

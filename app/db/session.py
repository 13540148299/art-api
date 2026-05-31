from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLAlchemy 数据库引擎。
# pool_pre_ping=True 会在连接池复用连接前主动探测连接是否可用，
# 可以减少 PostgreSQL 长连接被断开后首次请求报错的概率。
engine = create_engine(settings.database_url, pool_pre_ping=True)

# 数据库会话工厂。
# autocommit=False：所有写入都需要显式 commit，避免业务代码无意提交。
# autoflush=False：避免查询前自动 flush 未完成的变更，让事务边界更清晰。
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 数据库依赖。

    用法示例：
    `db: Session = Depends(get_db)`

    每次请求创建一个数据库会话，请求结束后自动关闭。
    业务层只负责 commit/rollback，连接释放由这里统一兜底。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

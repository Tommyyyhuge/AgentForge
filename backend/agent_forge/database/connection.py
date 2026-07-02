"""
AgentForge 数据库连接模块
"""
import asyncio
import os

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from agent_forge.config.settings import settings


class Base(DeclarativeBase):
    pass


# 创建异步引擎
def get_engine():
    """获取数据库引擎

    根据配置创建适当的异步引擎。
    SQLite 使用 aiosqlite，PostgreSQL 使用 asyncpg。
    """
    database_url = settings.DATABASE_URL

    # 如果是 SQLite，确保使用异步驱动
    if database_url.startswith("sqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        # 修复：自动创建数据库文件所在目录
        db_path = database_url.replace("sqlite+aiosqlite://", "").lstrip("/")
        if db_path and db_path != ":memory:":
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

    return create_async_engine(
        database_url,
        echo=settings.DEBUG,  # 开发环境打印 SQL
        poolclass=NullPool if settings.ENVIRONMENT == "development" else None,
    )


engine = get_engine()

# 创建异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    """获取数据库会话（异步生成器）

    用于 FastAPI 的依赖注入系统。
    自动处理会话的创建和关闭。

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库 — 使用 Alembic 迁移"""
    from alembic import command
    from alembic.config import Config
    from agent_forge.database import models  # noqa: F401

    alembic_ini = os.path.join(
        os.path.dirname(__file__), "..", "..", "alembic.ini"
    )
    alembic_cfg = Config(alembic_ini)
    # Alembic upgrade 是同步的，在线程池中执行避免阻塞事件循环
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")

    await bootstrap_provider_configs()


async def bootstrap_provider_configs():
    """Bootstrap Provider configs from existing legacy API keys."""
    from agent_forge.core.providers import ProviderConfigService

    async with async_session() as session:
        await ProviderConfigService().bootstrap_from_api_keys(session)


async def close_db():
    """关闭数据库连接

    在应用关闭时调用，释放连接池资源。
    """
    await engine.dispose()

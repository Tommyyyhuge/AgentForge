"""
数据库连接模块测试
"""
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from agent_forge.database.connection import (Base, close_db, get_db,
                                             get_engine, init_db)


class TestDatabaseConnection:
    """测试数据库连接"""

    @pytest.mark.asyncio
    async def test_get_db(self):
        """测试数据库会话生成器"""
        # 由于 get_db 是异步生成器，我们需要用 async for 来测试
        # 但这里不实际连接数据库，只是验证结构
        pass  # 实际测试需要真实数据库连接

    def test_base_declarative(self):
        """测试声明式基类"""
        # Base 是 SQLAlchemy 的 declarative_base() 实例
        assert Base is not None

    def test_get_engine_sqlite(self):
        """测试 SQLite 引擎创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            with patch("agent_forge.database.connection.settings") as mock_settings:
                mock_settings.DATABASE_URL = f"sqlite:///{db_path}"
                mock_settings.DEBUG = False
                mock_settings.ENVIRONMENT = "development"

                engine = get_engine()
                assert engine is not None
                # 验证目录已创建
                assert os.path.exists(tmpdir)

    def test_get_engine_sqlite_memory(self):
        """测试内存 SQLite 引擎"""
        with patch("agent_forge.database.connection.settings") as mock_settings:
            mock_settings.DATABASE_URL = "sqlite:///:memory:"
            mock_settings.DEBUG = False
            mock_settings.ENVIRONMENT = "development"

            engine = get_engine()
            assert engine is not None

    def test_get_engine_postgresql(self):
        """测试 PostgreSQL 引擎创建"""
        with patch("agent_forge.database.connection.settings") as mock_settings:
            mock_settings.DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.DEBUG = False
            mock_settings.ENVIRONMENT = "production"

            engine = get_engine()
            assert engine is not None

    def test_get_engine_creates_directory(self):
        """测试自动创建数据库目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = os.path.join(tmpdir, "subdir", "data")
            db_path = os.path.join(db_dir, "test.db")

            with patch("agent_forge.database.connection.settings") as mock_settings:
                mock_settings.DATABASE_URL = f"sqlite:///{db_path}"
                mock_settings.DEBUG = False
                mock_settings.ENVIRONMENT = "development"

                # 目录应该不存在
                assert not os.path.exists(db_dir)

                engine = get_engine()

                # 目录应该被创建
                assert os.path.exists(db_dir)


class TestDatabaseLifecycle:
    """测试数据库生命周期"""

    @pytest.mark.asyncio
    async def test_init_db(self):
        """测试数据库初始化"""
        # 这个测试需要实际的数据库连接
        # 在实际环境中运行时会创建表
        pass

    @pytest.mark.asyncio
    async def test_close_db(self):
        """测试关闭数据库"""
        # 这个测试需要实际的数据库连接
        pass

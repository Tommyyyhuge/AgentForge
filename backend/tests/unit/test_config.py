"""
配置模块测试
"""
import pytest

from agent_forge.config.settings import settings


class TestSettings:
    """测试配置类"""

    def test_settings_load(self):
        """测试配置加载"""
        assert settings.APP_NAME == "AgentForge"
        assert settings.ENVIRONMENT == "development"

    def test_database_config(self):
        """测试数据库配置"""
        assert settings.DB_TYPE == "sqlite"
        assert "sqlite" in settings.DATABASE_URL

    def test_jwt_config(self):
        """测试 JWT 配置"""
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_EXPIRE_DAYS == 7

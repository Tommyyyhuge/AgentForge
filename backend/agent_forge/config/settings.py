"""
AgentForge 配置管理模块
"""
from typing import Optional

from pydantic import ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类，自动从 .env 文件加载"""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # 应用信息
    APP_NAME: str = "AgentForge"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # 数据库
    DB_TYPE: str = "sqlite"
    DATABASE_URL: str = "sqlite:///data/agentforge.db"

    # JWT - 强制必须配置，开发环境提供默认值
    JWT_SECRET_KEY: SecretStr = Field(
        default="change-me-in-production-32-characters-long-key",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # 加密 - 强制必须配置，开发环境提供默认值
    ENCRYPTION_KEY: SecretStr = Field(
        default="change-me-in-production-32-characters-long-key",
        min_length=32,
    )
    ENCRYPTION_SALT: SecretStr = Field(default="change-me-in-production-salt")

    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # LLM API
    KIMI_API_KEY: Optional[str] = None
    KIMI_BASE_URL: str = "https://api.moonshot.cn"
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chromadb"

    # 监控
    ENABLE_MONITORING: bool = True
    METRICS_RETENTION_DAYS: int = 30

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


# 全局配置实例
settings = Settings()

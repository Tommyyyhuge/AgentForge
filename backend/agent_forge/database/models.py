"""
AgentForge ORM 模型定义

包含五个核心表：
- UserORM: 用户账号
- TaskORM: 任务记录
- StepORM: 任务执行步骤
- AgentStateORM: Agent 运行时状态
- MemoryORM: 长期记忆持久化（SQLite 降级存储）
"""
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_forge.database.connection import Base


class TaskORM(Base):
    """任务 ORM 模型

    支持层级任务结构（parent_id 自引用外键）。
    每个任务包含若干 StepORM 执行步骤。
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=True
    )
    task_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # 关联：一个任务包含多个步骤
    steps: Mapped[List["StepORM"]] = relationship(
        "StepORM", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TaskORM(id={self.id!r}, title={self.title!r}, status={self.status!r})>"


class StepORM(Base):
    """步骤 ORM 模型

    记录任务执行过程中的每一步操作。
    step_type 枚举值: thought / action / observation / final / error
    """

    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    agent_role: Mapped[str] = mapped_column(String, nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(
        String, nullable=False, comment="thought / action / observation / final / error"
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # 关联：每个步骤属于一个任务
    task: Mapped["TaskORM"] = relationship("TaskORM", back_populates="steps")

    def __repr__(self) -> str:
        return (
            f"<StepORM(id={self.id!r}, step_number={self.step_number!r}, "
            f"step_type={self.step_type!r})>"
        )


class AgentStateORM(Base):
    """Agent 状态 ORM 模型

    记录每个 Agent 角色的运行时状态，
    支持追踪当前正在执行的任务。
    """

    __tablename__ = "agent_states"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="idle")
    current_task_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AgentStateORM(id={self.id!r}, role={self.role!r}, "
            f"name={self.name!r}, status={self.status!r})>"
        )


class UserORM(Base):
    """用户 ORM 模型

    存储用户账号信息和密码哈希，
    用于 JWT 认证和授权。
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # 关联
    api_keys: Mapped[List["APIKeyORM"]] = relationship(
        "APIKeyORM", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<UserORM(id={self.id!r}, username={self.username!r}, "
            f"email={self.email!r})>"
        )


class MemoryORM(Base):
    """记忆 ORM 模型

    作为 ChromaDB 的 SQLite 降级存储。
    当 ChromaDB 不可用时，使用此表持久化长期记忆。
    每条记录包含文本内容、关联信息及可选的向量嵌入。
    """

    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    memory_type: Mapped[str] = mapped_column(
        String, default="long_term", comment="long_term / external"
    )
    agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=True, index=True
    )
    source: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="外部记忆来源"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return (
            f"<MemoryORM(id={self.id!r}, type={self.memory_type!r}, "
            f"content_preview={self.content[:40]!r}...)>"
        )


class APIKeyORM(Base):
    """API Key 加密存储 ORM 模型

    存储用户上传的第三方 LLM API Key，使用 PBKDF2 + Fernet 加密。
    支持权限分级：read（仅查看）、write（可调用 LLM）、admin（可管理）。
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(
        String, nullable=False, comment="kimi / deepseek"
    )
    encrypted_key: Mapped[str] = mapped_column(
        String, nullable=False, comment="PBKDF2 + Fernet 加密后的密文"
    )
    masked_key: Mapped[str] = mapped_column(
        String, nullable=False, comment="前端展示的掩码格式：sk-****-abcd"
    )
    permission: Mapped[str] = mapped_column(
        String, default="write", comment="read / write / admin"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # 关联
    user: Mapped["UserORM"] = relationship("UserORM", back_populates="api_keys")
    provider_configs: Mapped[List["ProviderConfigORM"]] = relationship(
        "ProviderConfigORM", back_populates="api_key"
    )

    def __repr__(self) -> str:
        return (
            f"<APIKeyORM(id={self.id!r}, provider={self.provider!r}, "
            f"masked={self.masked_key!r})>"
        )


class ProviderConfigORM(Base):
    """Persisted Provider configuration."""

    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    auth_type: Mapped[str] = mapped_column(String, default="api_key_bearer")
    api_key_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("api_keys.id"), nullable=True
    )
    default_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    rate_limit_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    streaming_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tool_calling_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    api_key: Mapped[Optional["APIKeyORM"]] = relationship(
        "APIKeyORM", back_populates="provider_configs"
    )
    models: Mapped[List["ModelConfigORM"]] = relationship(
        "ModelConfigORM",
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    health_checks: Mapped[List["ProviderHealthCheckORM"]] = relationship(
        "ProviderHealthCheckORM",
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ProviderConfigORM(id={self.id!r}, "
            f"provider_type={self.provider_type!r})>"
        )


class ModelConfigORM(Base):
    """Persisted model-level Provider configuration."""

    __tablename__ = "model_configs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider_id: Mapped[str] = mapped_column(
        String, ForeignKey("provider_configs.id"), nullable=False, index=True
    )
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supports_streaming: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    supports_tool_calling: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    supports_json_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    supports_vision: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    supports_embeddings: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    provider: Mapped["ProviderConfigORM"] = relationship(
        "ProviderConfigORM", back_populates="models"
    )

    def __repr__(self) -> str:
        return (
            f"<ModelConfigORM(id={self.id!r}, model_id={self.model_id!r}, "
            f"provider_id={self.provider_id!r})>"
        )


class ProviderHealthCheckORM(Base):
    """Persisted Provider connection test result."""

    __tablename__ = "provider_health_checks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider_id: Mapped[str] = mapped_column(
        String, ForeignKey("provider_configs.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model_tested: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    provider: Mapped["ProviderConfigORM"] = relationship(
        "ProviderConfigORM", back_populates="health_checks"
    )

    def __repr__(self) -> str:
        return (
            f"<ProviderHealthCheckORM(id={self.id!r}, "
            f"provider_id={self.provider_id!r}, status={self.status!r})>"
        )

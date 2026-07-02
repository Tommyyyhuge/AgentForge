"""
AgentForge 数据模型定义
"""
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(str, Enum):
    """Agent 角色枚举"""

    RESEARCHER = "researcher"
    CODER = "coder"
    WRITER = "writer"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"


class StepType(str, Enum):
    """步骤类型枚举"""

    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL = "final"
    ERROR = "error"



class Task(BaseModel):
    """任务模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """任务结果模型"""

    task_id: str
    status: TaskStatus
    output: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    steps_count: int = 0


class AgentStep(BaseModel):
    """Agent 执行步骤模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    agent_id: str
    agent_role: AgentRole
    step_number: int
    step_type: StepType
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    latency_ms: Optional[int] = None


class AgentState(BaseModel):
    """Agent 状态模型"""

    agent_id: str
    role: AgentRole
    current_task_id: Optional[str] = None
    status: str = "idle"  # idle, busy, error
    memory_context: List[str] = Field(default_factory=list)
    performance_stats: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """Agent 间消息模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: Optional[str] = None  # None 表示广播
    message_type: str  # request, response, broadcast
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: Optional[str] = None


class PlanNode(BaseModel):
    """计划节点模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_role: Optional[AgentRole] = None
    estimated_duration: Optional[int] = None  # 秒
    actual_duration: Optional[int] = None
    output: Optional[str] = None



class UserCreate(BaseModel):
    """用户注册请求体"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    """用户登录请求体"""

    username: str = Field(..., min_length=3, description="用户名")
    password: str = Field(..., min_length=6, description="密码")


class UserResponse(BaseModel):
    """用户信息响应体"""

    id: str
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT Token 响应体"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 解析后的数据"""

    username: Optional[str] = None

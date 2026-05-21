"""
AgentForge Agent 基类模块

所有 Agent 都必须继承 BaseAgent 并实现 execute 方法。
BaseAgent 提供了 Agent 生命周期管理、记忆系统和基础回调接口。
"""
import uuid
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_forge.core.cancellation import CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.models.schemas import AgentRole, AgentState, AgentStep
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Agent 抽象基类

    所有具体 Agent 必须继承此类并实现 execute 方法。
    提供统一的记忆管理、生命周期回调和状态跟踪。

    使用方式:
        class MyAgent(BaseAgent):
            role = AgentRole.EXECUTOR
            name = "MyAgent"
            description = "自定义 Agent"

            async def execute(self, task, context=None, cancellation_token=None):
                yield AgentStep(...)
    """

    role: AgentRole = AgentRole.EXECUTOR
    name: str = "BaseAgent"
    description: str = "Agent 基类"

    def __init__(self, llm_router: LLMRouter, tool_registry: Optional[Any] = None):
        """初始化 Agent

        Args:
            llm_router: LLM 路由器实例，用于与语言模型交互
            tool_registry: 工具注册中心（可选）
        """
        self.agent_id: str = str(uuid.uuid4())
        self.llm_router: LLMRouter = llm_router
        self.tool_registry = tool_registry
        self.state: AgentState = AgentState(
            agent_id=self.agent_id,
            role=self.role,
            status="idle",
        )
        self.memory: List[str] = []

    @abstractmethod
    async def execute(
        self,
        task: Any,
        context: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行任务（子类必须实现）

        这是 Agent 的核心方法，以异步生成器形式逐步产生执行步骤。
        每个步骤包含思考、行动、观察或最终结果。

        Args:
            task: 待执行的任务对象
            context: 可选的上下文信息
            cancellation_token: 可选的取消令牌

        Yields:
            AgentStep: 执行过程中的每个步骤
        """
        raise NotImplementedError

    def get_system_prompt(self) -> str:
        """获取系统提示词

        子类可重写此方法以提供自定义的系统提示词。
        系统提示词定义了 Agent 的角色定位和行为准则。

        Returns:
            系统提示词字符串
        """
        return (
            f"你是 {self.name}，一个 {self.description}。\n"
            f"请根据你的角色定位完成分配的任务。"
        )

    async def on_task_start(self, task: Any) -> None:
        """任务开始回调

        在 execute 开始时自动调用，可用于记录日志或初始化资源。

        Args:
            task: 即将执行的任务
        """
        self.state.status = "busy"
        if hasattr(task, 'id'):
            self.state.current_task_id = task.id
        logger.info(f"Agent {self.name} ({self.agent_id[:8]}...) 开始任务: {task}")

    async def on_task_complete(self, task: Any, result: Any) -> None:
        """任务完成回调

        在 execute 成功结束时自动调用。

        Args:
            task: 已完成的任务
            result: 执行结果
        """
        self.state.status = "idle"
        self.state.current_task_id = None
        logger.info(f"Agent {self.name} ({self.agent_id[:8]}...) 完成任务")

    async def on_task_error(self, task: Any, error: Exception) -> None:
        """任务错误回调

        在 execute 抛出异常时自动调用。

        Args:
            task: 执行失败的任务
            error: 捕获到的异常
        """
        self.state.status = "error"
        logger.error(f"Agent {self.name} ({self.agent_id[:8]}...) 任务失败: {error}")

    def add_to_memory(self, content: str) -> None:
        """添加记忆

        将一条内容添加到 Agent 的记忆列表中。

        Args:
            content: 消息内容
        """
        self.memory.append(content)
        # 超过 100 条时截断到最近 50 条
        if len(self.memory) > 100:
            self.memory = self.memory[-50:]

    def clear_memory(self) -> None:
        """清空记忆"""
        self.memory.clear()

    def get_memory_context(self) -> str:
        """获取记忆上下文

        将 Agent 记忆列表格式化为字符串，便于拼接到提示词中。

        Returns:
            格式化的上下文字符串
        """
        return "\n".join(self.memory)

    def get_state(self) -> AgentState:
        """获取 Agent 当前状态"""
        return self.state

    def update_performance(self, metric: str, value: float) -> None:
        """更新性能统计

        Args:
            metric: 指标名称
            value: 指标值
        """
        self.state.performance_stats[metric] = value

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"agent_id={self.agent_id[:8]}..., "
            f"role={self.role.value}, "
            f"name={self.name})"
        )

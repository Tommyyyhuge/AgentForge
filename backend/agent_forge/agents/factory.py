"""
AgentForge Agent 工厂模块

负责 Agent 的注册、创建和管理。
通过工厂模式统一管理所有 Agent 角色类型。
"""
from typing import Dict, List

from agent_forge.agents.base import BaseAgent
from agent_forge.core.llm_client import LLMRouter
from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.models.schemas import AgentRole
from agent_forge.utils.logging import get_logger
from typing import Optional

logger = get_logger(__name__)


class AgentFactory:
    """Agent 工厂类

    注册和管理 Agent 角色类型，按需创建 Agent 实例。

    使用方式:
        # 注册 Agent 类型
        AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
        AgentFactory.register(AgentRole.RESEARCHER, ResearcherAgent)

        # 创建 Agent 实例
        agent = AgentFactory.create(AgentRole.EXECUTOR, llm_router)
    """

    _registry: Dict[AgentRole, type] = {}

    @classmethod
    def register(cls, role: AgentRole, agent_class: type):
        """注册 Agent 类

        将 Agent 角色与其对应的实现类绑定。

        Args:
            role: Agent 角色枚举值
            agent_class: Agent 实现类（必须继承 BaseAgent）

        Raises:
            TypeError: agent_class 不是 BaseAgent 的子类时抛出
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(
                f"agent_class 必须是 BaseAgent 的子类，得到 {agent_class.__name__}"
            )

        cls._registry[role] = agent_class
        logger.info(f"已注册 Agent 类: {role.value} -> {agent_class.__name__}")

    @classmethod
    def create(
        cls,
        role: AgentRole,
        llm_router: LLMRouter,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> BaseAgent:
        """创建 Agent 实例

        根据角色类型创建对应的 Agent 实例。

        Args:
            role: Agent 角色
            llm_router: LLM 路由器实例
            tool_registry: 工具注册中心（可选，传递给支持工具的 Agent）

        Returns:
            BaseAgent 实例

        Raises:
            ValueError: 角色未注册时抛出
        """
        if role not in cls._registry:
            raise ValueError(
                f"未注册的 Agent 角色: {role.value}。"
                f"可用的角色: {[r.value for r in cls._registry.keys()]}"
            )

        agent_class = cls._registry[role]

        # 检查 Agent 是否支持 tool_registry 参数
        import inspect
        init_params = inspect.signature(agent_class.__init__).parameters
        if "tool_registry" in init_params:
            agent = agent_class(llm_router, tool_registry=tool_registry)
        else:
            agent = agent_class(llm_router)

        logger.info(f"创建 Agent: {role.value} ({agent.agent_id[:8]}...)")
        return agent

    @classmethod
    def list_roles(cls) -> List[AgentRole]:
        """列出所有已注册的角色

        Returns:
            AgentRole 列表
        """
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, role: AgentRole) -> bool:
        """检查角色是否已注册

        Args:
            role: Agent 角色

        Returns:
            是否已注册
        """
        return role in cls._registry

    @classmethod
    def unregister(cls, role: AgentRole):
        """取消注册 Agent 角色

        Args:
            role: Agent 角色
        """
        if role in cls._registry:
            agent_class = cls._registry.pop(role)
            logger.info(f"已取消注册 Agent: {role.value} -> {agent_class.__name__}")

    @classmethod
    def clear_registry(cls):
        """清空所有注册"""
        cls._registry.clear()
        logger.info("已清空所有 Agent 注册")


def _register_builtin_agents():
    """注册内置 Agent 类型（延迟导入避免循环依赖）"""
    from agent_forge.agents.executor_agent import ExecutorAgent
    from agent_forge.agents.researcher_agent import ResearcherAgent
    from agent_forge.agents.coder_agent import CoderAgent
    from agent_forge.agents.writer_agent import WriterAgent
    from agent_forge.agents.reviewer_agent import ReviewerAgent

    AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
    AgentFactory.register(AgentRole.RESEARCHER, ResearcherAgent)
    AgentFactory.register(AgentRole.CODER, CoderAgent)
    AgentFactory.register(AgentRole.WRITER, WriterAgent)
    AgentFactory.register(AgentRole.REVIEWER, ReviewerAgent)


# 模块导入时自动注册内置 Agent
_register_builtin_agents()

"""
Agent 模块测试

测试 ExecutorAgent、ResearcherAgent 的创建、执行和 AgentFactory 的注册管理。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_forge.agents.base import BaseAgent
from agent_forge.agents.executor_agent import ExecutorAgent
from agent_forge.agents.factory import AgentFactory
from agent_forge.agents.researcher_agent import ResearcherAgent
from agent_forge.core.llm_client import LLMResponse, LLMRouter
from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.models.schemas import AgentRole, AgentStep, StepType, Task, TaskStatus
from agent_forge.tools.base import BaseTool, ToolSchema


# =============================================================================
# Mock 对象
# =============================================================================


def _mock_llm_router() -> MagicMock:
    """创建 Mock LLMRouter"""
    router = MagicMock(spec=LLMRouter)
    router.route = AsyncMock(
        return_value=LLMResponse(content="mock response", model="test-model")
    )
    return router


class _MockSearchTool(BaseTool):
    """模拟搜索工具"""
    name = "web_search"
    description = "模拟 Web 搜索工具"

    def _build_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={"query": {"type": "string"}},
            required=["query"],
        )

    async def execute(self, **kwargs) -> str:
        return f"搜索结果: {kwargs.get('query', '')}"


# =============================================================================
# TestExecutorAgent
# =============================================================================


class TestExecutorAgent:
    """测试 ExecutorAgent"""

    @pytest.fixture
    def router(self):
        return _mock_llm_router()

    @pytest.fixture
    def tool_registry(self):
        registry = ToolRegistry()
        registry.register(_MockSearchTool())
        return registry

    def test_executor_creation(self, router):
        """ExecutorAgent 正确创建"""
        agent = ExecutorAgent(llm_router=router)
        assert agent.role == AgentRole.EXECUTOR
        assert agent.name == "Executor"
        assert agent.agent_id is not None
        assert isinstance(agent, BaseAgent)

    def test_executor_with_tools(self, router, tool_registry):
        """ExecutorAgent 携带工具注册中心"""
        agent = ExecutorAgent(llm_router=router, tool_registry=tool_registry)
        assert agent.tool_registry is tool_registry
        assert "web_search" in tool_registry

    def test_executor_tools_default_none(self, router):
        """默认不提供 tool_registry"""
        agent = ExecutorAgent(llm_router=router)
        assert agent.tool_registry is None

    def test_get_system_prompt(self, router):
        """获取系统提示词"""
        agent = ExecutorAgent(llm_router=router)
        prompt = agent.get_system_prompt()
        assert "任务执行者" in prompt
        assert "高效" in prompt

    def test_get_system_prompt_with_tools(self, router, tool_registry):
        """带工具的提示词包含工具列表"""
        agent = ExecutorAgent(llm_router=router, tool_registry=tool_registry)
        prompt = agent.get_system_prompt()
        assert "web_search" in prompt

    @pytest.mark.asyncio
    async def test_execute_yields_steps(self, router):
        """execute() 产出正确的步骤序列"""
        agent = ExecutorAgent(llm_router=router)
        task = Task(title="测试任务", description="测试描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        # 应产出: THOUGHT → ACTION → OBSERVATION → FINAL (4 步)
        assert len(steps) == 4
        assert steps[0].step_type == StepType.THOUGHT
        assert steps[1].step_type == StepType.ACTION
        assert steps[2].step_type == StepType.OBSERVATION
        assert steps[3].step_type == StepType.FINAL
        assert all(isinstance(s, AgentStep) for s in steps)

    @pytest.mark.asyncio
    async def test_execute_calls_llm(self, router):
        """execute() 调用了 LLM"""
        agent = ExecutorAgent(llm_router=router)
        task = Task(title="任务", description="描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        # LLM router 的 route 方法被调用
        router.route.assert_called()

    @pytest.mark.asyncio
    async def test_execute_updates_state(self, router):
        """执行过程中更新 Agent 状态（开始时 busy，异常或完成后更新）"""
        agent = ExecutorAgent(llm_router=router)
        task = Task(title="任务", description="描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        # ExecutorAgent 执行完成后由 base 的 on_task_complete 更新为 idle
        # 注意：on_task_complete 在 execute 的 call-site（Orchestrator）而非 execute 内部调用
        assert agent.state.status in ("busy", "idle")
        assert agent.state.current_task_id == task.id


# =============================================================================
# TestResearcherAgent
# =============================================================================


class TestResearcherAgent:
    """测试 ResearcherAgent"""

    @pytest.fixture
    def router(self):
        return _mock_llm_router()

    @pytest.fixture
    def tool_registry_with_search(self):
        registry = ToolRegistry()
        registry.register(_MockSearchTool())
        return registry

    def test_researcher_creation(self, router):
        """ResearcherAgent 正确创建"""
        agent = ResearcherAgent(llm_router=router)
        assert agent.role == AgentRole.RESEARCHER
        assert agent.name == "Researcher"
        assert isinstance(agent, BaseAgent)

    def test_researcher_get_system_prompt(self, router):
        """获取研究员系统提示词"""
        agent = ResearcherAgent(llm_router=router)
        prompt = agent.get_system_prompt()
        assert "研究员" in prompt
        assert "WebSearch" in prompt

    @pytest.mark.asyncio
    async def test_researcher_search_with_tools(self, router, tool_registry_with_search):
        """带搜索工具时 _try_search 返回结果"""
        agent = ResearcherAgent(
            llm_router=router, tool_registry=tool_registry_with_search
        )
        task = Task(title="搜索测试", description="搜索关键词")

        result = await agent._try_search(task)
        assert result is not None
        assert "搜索结果" in result

    @pytest.mark.asyncio
    async def test_researcher_search_without_tools(self, router):
        """无工具时 _try_search 返回 None"""
        agent = ResearcherAgent(llm_router=router)
        task = Task(title="搜索测试", description="搜索关键词")

        result = await agent._try_search(task)
        assert result is None

    @pytest.mark.asyncio
    async def test_researcher_execute_with_search(self, router, tool_registry_with_search):
        """执行研究任务并产出步骤"""
        agent = ResearcherAgent(
            llm_router=router, tool_registry=tool_registry_with_search
        )
        task = Task(title="研究任务", description="研究XXXX")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        # 应包含 THOUGHT, ACTION, OBSERVATION(搜索), OBSERVATION(LLM), FINAL
        assert len(steps) >= 3
        thought_types = [s.step_type for s in steps]
        assert StepType.THOUGHT in thought_types
        assert StepType.FINAL in thought_types


# =============================================================================
# TestAgentFactory
# =============================================================================


class TestAgentFactory:
    """测试 AgentFactory 工厂类（使用 agents.factory 版本）"""

    def setup_method(self):
        """每个测试前清理 registry 副作用"""
        AgentFactory.clear_registry()

    def teardown_method(self):
        AgentFactory.clear_registry()

    def test_register_valid_agent(self):
        """注册有效的 Agent 子类"""
        AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
        assert AgentFactory.is_registered(AgentRole.EXECUTOR)

    def test_register_invalid_class(self):
        """注册非 BaseAgent 子类抛出 TypeError"""

        class NotAnAgent:
            pass

        with pytest.raises(TypeError, match="BaseAgent 的子类"):
            AgentFactory.register(AgentRole.EXECUTOR, NotAnAgent)

    def test_factory_create(self):
        """Factory 创建 Agent 实例"""
        router = _mock_llm_router()
        # 重新注册（setup_method 已清理）
        AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
        AgentFactory.register(AgentRole.RESEARCHER, ResearcherAgent)

        executor = AgentFactory.create(AgentRole.EXECUTOR, llm_router=router)
        assert isinstance(executor, ExecutorAgent)
        assert executor.role == AgentRole.EXECUTOR

        researcher = AgentFactory.create(AgentRole.RESEARCHER, llm_router=router)
        assert isinstance(researcher, ResearcherAgent)

    def test_factory_create_with_tool_registry(self):
        """Factory 创建 Agent 时传递 tool_registry"""
        router = _mock_llm_router()
        registry = ToolRegistry()
        AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)

        agent = AgentFactory.create(
            AgentRole.EXECUTOR, llm_router=router, tool_registry=registry
        )
        assert agent.tool_registry is registry

    def test_factory_unknown_role(self):
        """创建未注册角色抛出 ValueError"""
        router = _mock_llm_router()

        with pytest.raises(ValueError, match="未注册的 Agent 角色"):
            AgentFactory.create(AgentRole.WRITER, llm_router=router)

    def test_list_roles(self):
        """列出已注册角色"""
        AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
        roles = AgentFactory.list_roles()
        assert AgentRole.EXECUTOR in roles

    def test_unregister(self):
        """取消注册角色"""
        AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
        AgentFactory.unregister(AgentRole.EXECUTOR)
        assert not AgentFactory.is_registered(AgentRole.EXECUTOR)

    def test_unregister_nonexistent(self):
        """取消注册不存在的角色无异常"""
        AgentFactory.unregister(AgentRole.WRITER)

    def test_clear_registry(self):
        """清空所有注册"""
        AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
        AgentFactory.register(AgentRole.RESEARCHER, ResearcherAgent)
        AgentFactory.clear_registry()
        assert len(AgentFactory.list_roles()) == 0


# =============================================================================
# TestBaseAgent
# =============================================================================


class TestBaseAgent:
    """测试 BaseAgent 基础功能（通过 ExecutorAgent 实例）"""

    @pytest.fixture
    def agent(self):
        return ExecutorAgent(llm_router=_mock_llm_router())

    def test_add_to_memory(self, agent):
        """添加到短期记忆"""
        agent.add_to_memory("记忆片段1")
        agent.add_to_memory("记忆片段2")
        assert "记忆片段1" in agent.memory
        assert len(agent.memory) == 2

    def test_memory_truncation(self, agent):
        """记忆超过 100 条时截断到最近 50 条（截断后继续追加）"""
        for i in range(120):
            agent.add_to_memory(f"记忆{i}")
        # 超过 100 条时触发一次截断到 50 条，后续 19 条继续追加 = 69
        assert len(agent.memory) <= 70, f"截断逻辑: 50 + 后续追加，实际: {len(agent.memory)}"

    def test_clear_memory(self, agent):
        """清空短期记忆"""
        agent.add_to_memory("记忆")
        agent.clear_memory()
        assert len(agent.memory) == 0

    def test_get_state(self, agent):
        """获取 Agent 状态"""
        state = agent.get_state()
        assert state.agent_id == agent.agent_id
        assert state.role == AgentRole.EXECUTOR
        assert state.status == "idle"

    def test_update_performance(self, agent):
        """更新性能统计"""
        agent.update_performance("avg_latency_ms", 350)
        assert agent.state.performance_stats["avg_latency_ms"] == 350

    def test_repr(self, agent):
        """__repr__ 返回可读字符串"""
        rep = repr(agent)
        assert "ExecutorAgent" in rep
        assert agent.agent_id[:8] in rep

    @pytest.mark.asyncio
    async def test_on_task_lifecycle(self, agent):
        """测试任务生命周期回调"""
        task = Task(title="测试", description="描述")

        await agent.on_task_start(task)
        assert agent.state.status == "busy"
        assert agent.state.current_task_id == task.id

        from agent_forge.models.schemas import TaskResult
        result = TaskResult(task_id=task.id, status=TaskStatus.COMPLETED)
        await agent.on_task_complete(task, result)
        assert agent.state.status == "idle"
        assert agent.state.current_task_id is None

        await agent.on_task_error(task, ValueError("测试错误"))
        assert agent.state.status == "error"

"""
新 Agent 模块测试

测试 CoderAgent、WriterAgent、ReviewerAgent 的创建、执行和工厂注册。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_forge.agents.base import BaseAgent
from agent_forge.agents.coder_agent import CoderAgent
from agent_forge.agents.factory import AgentFactory
from agent_forge.agents.writer_agent import WriterAgent
from agent_forge.agents.reviewer_agent import ReviewerAgent
from agent_forge.core.llm_client import LLMResponse, LLMRouter
from agent_forge.models.schemas import AgentRole, AgentStep, StepType, Task


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


# =============================================================================
# TestCoderAgent
# =============================================================================


class TestCoderAgent:
    """测试 CoderAgent"""

    @pytest.fixture
    def router(self):
        return _mock_llm_router()

    def test_coder_creation(self, router):
        """CoderAgent 正确创建"""
        agent = CoderAgent(llm_router=router)
        assert agent.role == AgentRole.CODER
        assert agent.name == "Coder"
        assert agent.agent_id is not None
        assert isinstance(agent, BaseAgent)

    def test_coder_tool_registry_default_none(self, router):
        """默认不提供 tool_registry"""
        agent = CoderAgent(llm_router=router)
        assert agent.tool_registry is None

    def test_coder_get_system_prompt(self, router):
        """获取程序员系统提示词"""
        agent = CoderAgent(llm_router=router)
        prompt = agent.get_system_prompt()
        assert "程序员" in prompt
        assert "代码" in prompt
        assert "调试" in prompt
        assert "code_execute" in prompt

    @pytest.mark.asyncio
    async def test_coder_execute_yields_steps(self, router):
        """execute() 产出正确的步骤序列"""
        agent = CoderAgent(llm_router=router)
        task = Task(title="实现排序算法", description="用 Python 实现快速排序")

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
    async def test_coder_execute_calls_llm(self, router):
        """execute() 调用了 LLM"""
        agent = CoderAgent(llm_router=router)
        task = Task(title="代码任务", description="修复 bug")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        # LLM router 的 route 方法被调用
        router.route.assert_called()

    @pytest.mark.asyncio
    async def test_coder_execute_updates_state(self, router):
        """执行过程中更新 Agent 状态"""
        agent = CoderAgent(llm_router=router)
        task = Task(title="代码任务", description="实现功能")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        assert agent.state.status in ("busy", "idle")
        assert agent.state.current_task_id == task.id

    @pytest.mark.asyncio
    async def test_coder_execute_with_context(self, router):
        """execute() 传递上下文参数"""
        agent = CoderAgent(llm_router=router)
        task = Task(title="代码任务", description="描述")
        context = "已有代码: def foo(): pass"

        steps = []
        async for step in agent.execute(task, context=context):
            steps.append(step)

        assert len(steps) == 4
        assert steps[3].step_type == StepType.FINAL

    @pytest.mark.asyncio
    async def test_coder_execute_step_numbers_increment(self, router):
        """execute() 步骤编号递增"""
        agent = CoderAgent(llm_router=router)
        task = Task(title="代码任务", description="描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        for i, s in enumerate(steps, start=1):
            assert s.step_number == i

    @pytest.mark.asyncio
    async def test_coder_execute_agent_id_consistent(self, router):
        """execute() 所有步骤使用相同的 agent_id"""
        agent = CoderAgent(llm_router=router)
        task = Task(title="代码任务", description="描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        agent_ids = {s.agent_id for s in steps}
        assert len(agent_ids) == 1
        assert agent_ids.pop() == agent.agent_id


# =============================================================================
# TestWriterAgent
# =============================================================================


class TestWriterAgent:
    """测试 WriterAgent"""

    @pytest.fixture
    def router(self):
        return _mock_llm_router()

    def test_writer_creation(self, router):
        """WriterAgent 正确创建"""
        agent = WriterAgent(llm_router=router)
        assert agent.role == AgentRole.WRITER
        assert agent.name == "Writer"
        assert agent.agent_id is not None
        assert isinstance(agent, BaseAgent)

    def test_writer_tool_registry_default_none(self, router):
        """默认不提供 tool_registry"""
        agent = WriterAgent(llm_router=router)
        assert agent.tool_registry is None

    def test_writer_get_system_prompt(self, router):
        """获取作家系统提示词"""
        agent = WriterAgent(llm_router=router)
        prompt = agent.get_system_prompt()
        assert "作家" in prompt
        assert "文档" in prompt
        assert "summarize" in prompt

    @pytest.mark.asyncio
    async def test_writer_execute_yields_steps(self, router):
        """execute() 产出正确的步骤序列"""
        agent = WriterAgent(llm_router=router)
        task = Task(title="编写 API 文档", description="为 REST API 编写文档")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        assert len(steps) == 4
        assert steps[0].step_type == StepType.THOUGHT
        assert steps[1].step_type == StepType.ACTION
        assert steps[2].step_type == StepType.OBSERVATION
        assert steps[3].step_type == StepType.FINAL
        assert all(isinstance(s, AgentStep) for s in steps)

    @pytest.mark.asyncio
    async def test_writer_execute_calls_llm(self, router):
        """execute() 调用了 LLM"""
        agent = WriterAgent(llm_router=router)
        task = Task(title="写作任务", description="写一篇博客")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        router.route.assert_called()

    @pytest.mark.asyncio
    async def test_writer_execute_updates_state(self, router):
        """执行过程中更新 Agent 状态"""
        agent = WriterAgent(llm_router=router)
        task = Task(title="写作任务", description="写文档")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        assert agent.state.status in ("busy", "idle")
        assert agent.state.current_task_id == task.id

    @pytest.mark.asyncio
    async def test_writer_execute_with_context(self, router):
        """execute() 传递上下文参数"""
        agent = WriterAgent(llm_router=router)
        task = Task(title="写作任务", description="描述")
        context = "目标读者: 初级开发者"

        steps = []
        async for step in agent.execute(task, context=context):
            steps.append(step)

        assert len(steps) == 4


# =============================================================================
# TestReviewerAgent
# =============================================================================


class TestReviewerAgent:
    """测试 ReviewerAgent"""

    @pytest.fixture
    def router(self):
        return _mock_llm_router()

    def test_reviewer_creation(self, router):
        """ReviewerAgent 正确创建"""
        agent = ReviewerAgent(llm_router=router)
        assert agent.role == AgentRole.REVIEWER
        assert agent.name == "Reviewer"
        assert agent.agent_id is not None
        assert isinstance(agent, BaseAgent)

    def test_reviewer_tool_registry_default_none(self, router):
        """默认不提供 tool_registry"""
        agent = ReviewerAgent(llm_router=router)
        assert agent.tool_registry is None

    def test_reviewer_get_system_prompt(self, router):
        """获取审查员系统提示词"""
        agent = ReviewerAgent(llm_router=router)
        prompt = agent.get_system_prompt()
        assert "审查" in prompt
        assert "代码审查" in prompt
        assert "file_read" in prompt

    @pytest.mark.asyncio
    async def test_reviewer_execute_yields_steps(self, router):
        """execute() 产出正确的步骤序列"""
        agent = ReviewerAgent(llm_router=router)
        task = Task(title="审查代码", description="审查 PR 代码质量")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        assert len(steps) == 4
        assert steps[0].step_type == StepType.THOUGHT
        assert steps[1].step_type == StepType.ACTION
        assert steps[2].step_type == StepType.OBSERVATION
        assert steps[3].step_type == StepType.FINAL
        assert all(isinstance(s, AgentStep) for s in steps)

    @pytest.mark.asyncio
    async def test_reviewer_execute_calls_llm(self, router):
        """execute() 调用了 LLM"""
        agent = ReviewerAgent(llm_router=router)
        task = Task(title="审查任务", description="审查文档")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        router.route.assert_called()

    @pytest.mark.asyncio
    async def test_reviewer_execute_updates_state(self, router):
        """执行过程中更新 Agent 状态"""
        agent = ReviewerAgent(llm_router=router)
        task = Task(title="审查任务", description="审查代码")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        assert agent.state.status in ("busy", "idle")
        assert agent.state.current_task_id == task.id

    @pytest.mark.asyncio
    async def test_reviewer_execute_with_context(self, router):
        """execute() 传递上下文"""
        agent = ReviewerAgent(llm_router=router)
        task = Task(title="审查任务", description="描述")
        context = "审查标准: PEP 8"

        steps = []
        async for step in agent.execute(task, context=context):
            steps.append(step)

        assert len(steps) == 4


# =============================================================================
# TestAgentFactoryRegistration
# =============================================================================


class TestNewAgentFactoryRegistration:
    """测试工厂中新 Agent 的注册"""

    @pytest.fixture
    def router(self):
        return _mock_llm_router()

    def test_coder_registered(self):
        """CoderAgent 已在工厂中注册"""
        assert AgentFactory.is_registered(AgentRole.CODER)

    def test_writer_registered(self):
        """WriterAgent 已在工厂中注册"""
        assert AgentFactory.is_registered(AgentRole.WRITER)

    def test_reviewer_registered(self):
        """ReviewerAgent 已在工厂中注册"""
        assert AgentFactory.is_registered(AgentRole.REVIEWER)

    def test_factory_create_coder(self, router):
        """工厂创建 CoderAgent 实例"""
        agent = AgentFactory.create(AgentRole.CODER, router)
        assert isinstance(agent, CoderAgent)
        assert agent.role == AgentRole.CODER

    def test_factory_create_writer(self, router):
        """工厂创建 WriterAgent 实例"""
        agent = AgentFactory.create(AgentRole.WRITER, router)
        assert isinstance(agent, WriterAgent)
        assert agent.role == AgentRole.WRITER

    def test_factory_create_reviewer(self, router):
        """工厂创建 ReviewerAgent 实例"""
        agent = AgentFactory.create(AgentRole.REVIEWER, router)
        assert isinstance(agent, ReviewerAgent)
        assert agent.role == AgentRole.REVIEWER

    def test_factory_list_includes_new_roles(self, router):
        """工厂角色列表包含新角色"""
        roles = AgentFactory.list_roles()
        assert AgentRole.CODER in roles
        assert AgentRole.WRITER in roles
        assert AgentRole.REVIEWER in roles


# =============================================================================
# TestErrorHandling
# =============================================================================


class TestNewAgentErrorHandling:
    """测试新 Agent 的错误处理"""

    @pytest.fixture
    def router(self):
        return _mock_llm_router()

    @pytest.mark.asyncio
    async def test_coder_execute_error_yields_error_step(self, router):
        """execute 异常时产出 ERROR 步骤"""
        agent = CoderAgent(llm_router=router)
        router.route.side_effect = RuntimeError("模拟 LLM 调用失败")
        task = Task(title="代码任务", description="描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        # 正常情况下抛出异常后 yield ERROR step
        # 但这里 route 在 thought step 之后被调用，所以第一个 thought step 已产出
        assert steps[-1].step_type == StepType.ERROR
        assert "出错" in steps[-1].content or "失败" in steps[-1].content

    @pytest.mark.asyncio
    async def test_writer_execute_error_yields_error_step(self, router):
        """WriterAgent 异常时产出 ERROR 步骤"""
        agent = WriterAgent(llm_router=router)
        router.route.side_effect = RuntimeError("模拟 LLM 调用失败")
        task = Task(title="写作任务", description="描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        assert steps[-1].step_type == StepType.ERROR

    @pytest.mark.asyncio
    async def test_reviewer_execute_error_yields_error_step(self, router):
        """ReviewerAgent 异常时产出 ERROR 步骤"""
        agent = ReviewerAgent(llm_router=router)
        router.route.side_effect = RuntimeError("模拟 LLM 调用失败")
        task = Task(title="审查任务", description="描述")

        steps = []
        async for step in agent.execute(task):
            steps.append(step)

        assert steps[-1].step_type == StepType.ERROR

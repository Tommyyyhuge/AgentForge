"""
任务编排器模块测试

测试 Orchestrator 的节点执行、并行调度、取消、超时和并发控制。
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_forge.core.cancellation import CancellationError, CancellationToken
from agent_forge.core.llm_client import LLMResponse
from agent_forge.core.orchestrator import Orchestrator
from agent_forge.core.planner import PlanGraph, PlanNode
from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.models.schemas import AgentRole, AgentStep, StepType, Task, TaskStatus


# =============================================================================
# Mock Agent - 用于编排器测试
# =============================================================================


class _MockAgentSteps:
    """模拟 Agent 产出固定步骤列表"""

    def __init__(self, agent_id: str = "mock-agent", role: AgentRole = AgentRole.EXECUTOR):
        self.agent_id = agent_id
        self.role = role
        self.state = MagicMock(status="idle")

    async def execute(self, task, context=None, cancellation_token=None):
        """产出 THOUGHT → ACTION → OBSERVATION → FINAL"""
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=1,
            step_type=StepType.THOUGHT,
            content=f"分析任务: {task.title}",
        )
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=2,
            step_type=StepType.ACTION,
            content=f"执行: {task.title}",
        )
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=3,
            step_type=StepType.FINAL,
            content=f"完成: {task.title}",
        )

    async def on_task_start(self, task):
        self.state.status = "busy"

    async def on_task_complete(self, task, result):
        self.state.status = "idle"

    async def on_task_error(self, task, error):
        self.state.status = "error"


class _SlowMockAgent:
    """模拟执行耗时长的 Agent"""

    def __init__(self, delay: float = 10.0, agent_id: str = "slow-agent"):
        self.agent_id = agent_id
        self.role = AgentRole.EXECUTOR
        self.state = MagicMock(status="idle")
        self._delay = delay

    async def execute(self, task, context=None, cancellation_token=None):
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=1,
            step_type=StepType.THOUGHT,
            content="开始慢任务...",
        )
        await asyncio.sleep(self._delay)
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=2,
            step_type=StepType.FINAL,
            content="慢任务完成",
        )

    async def on_task_start(self, task):
        self.state.status = "busy"

    async def on_task_complete(self, task, result):
        self.state.status = "idle"

    async def on_task_error(self, task, error):
        self.state.status = "error"


class _CancelableMockAgent:
    """模拟可被取消的 Agent"""

    def __init__(self, agent_id: str = "cancel-agent", role: AgentRole = AgentRole.EXECUTOR):
        self.agent_id = agent_id
        self.role = role
        self.state = MagicMock(status="idle")

    async def execute(self, task, context=None, cancellation_token=None):
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=1,
            step_type=StepType.THOUGHT,
            content="开始任务",
        )
        # 检查取消令牌
        if cancellation_token:
            await cancellation_token.check_cancellation()
        # 继续产出
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=2,
            step_type=StepType.FINAL,
            content="完成",
        )

    async def on_task_start(self, task):
        self.state.status = "busy"

    async def on_task_complete(self, task, result):
        self.state.status = "idle"

    async def on_task_error(self, task, error):
        self.state.status = "error"


# =============================================================================
# 辅助
# =============================================================================


def _make_plan(nodes: dict, root_id: str = "") -> PlanGraph:
    """快捷构造 PlanGraph"""
    return PlanGraph(nodes=nodes, root_node_id=root_id or (list(nodes.keys())[0] if nodes else ""))


def _make_orchestrator(max_concurrency: int = 3) -> Orchestrator:
    """构造 Orchestrator 并注入 mock 依赖"""
    llm_router = MagicMock()
    llm_router.route = AsyncMock(
        return_value=LLMResponse(content="mock response", model="test")
    )
    tool_registry = ToolRegistry()
    orch = Orchestrator(
        llm_router=llm_router,
        tool_registry=tool_registry,
        max_concurrency=max_concurrency,
    )
    # 覆盖超时方便测试
    orch._max_timeout = 5.0
    return orch


# =============================================================================
# TestOrchestrator
# =============================================================================


class TestOrchestrator:
    """测试 Orchestrator"""

    @pytest.mark.asyncio
    async def test_execute_single_node(self):
        """单节点执行 - 基本路径"""
        node = PlanNode(id="n1", description="单一任务")
        plan = _make_plan({"n1": node})

        orch = _make_orchestrator()
        mock_agent = _MockAgentSteps(agent_id="agent-1")
        orch._get_or_create_agent = MagicMock(return_value=mock_agent)

        steps = []
        async for step in orch.execute_plan(plan):
            steps.append(step)

        assert len(steps) == 3
        assert steps[0].step_type == StepType.THOUGHT
        assert steps[1].step_type == StepType.ACTION
        assert steps[2].step_type == StepType.FINAL
        assert node.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        """层内并行执行 - 两个同层节点应并发运行"""
        node_a = PlanNode(id="A", description="节点A", dependencies=[])
        node_b = PlanNode(id="B", description="节点B", dependencies=[])
        plan = _make_plan({"A": node_a, "B": node_b})

        orch = _make_orchestrator(max_concurrency=5)
        orch._get_or_create_agent = MagicMock(return_value=_MockAgentSteps())

        steps = []
        async for step in orch.execute_plan(plan):
            steps.append(step)

        # 两个节点各 3 个步骤 = 6 个步骤
        assert len(steps) == 6
        assert node_a.status == TaskStatus.COMPLETED
        assert node_b.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_sequential(self):
        """层间顺序执行 - 下游节点依赖上游完成"""
        node_a = PlanNode(id="A", description="上游", dependencies=[])
        node_b = PlanNode(id="B", description="下游", dependencies=["A"])
        plan = _make_plan({"A": node_a, "B": node_b})

        orch = _make_orchestrator()
        orch._get_or_create_agent = MagicMock(return_value=_MockAgentSteps())

        steps = []
        async for step in orch.execute_plan(plan):
            steps.append(step)

        # A 先完成，B 后完成
        assert len(steps) == 6  # 2 nodes × 3 steps
        assert node_a.status == TaskStatus.COMPLETED
        assert node_b.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_cancellation(self):
        """取消执行 - 取消令牌触发后停止后续层"""
        node_a = PlanNode(id="A", description="第一层", dependencies=[])
        node_b = PlanNode(id="B", description="第二层", dependencies=["A"])
        plan = _make_plan({"A": node_a, "B": node_b})

        orch = _make_orchestrator()
        orch._get_or_create_agent = MagicMock(return_value=_MockAgentSteps())

        # 设置取消令牌（在第一个节点完成后触发）
        cancel_token = CancellationToken()

        steps = []
        # 重写 _execute_layer 让取消在 A 完成后触发
        original_execute_layer = orch._execute_layer

        async def _canceling_layer(*args, **kwargs):
            result = await original_execute_layer(*args, **kwargs)
            await cancel_token.cancel("手动取消")
            return result

        orch._execute_layer = _canceling_layer

        with pytest.raises(CancellationError):
            async for step in orch.execute_plan(plan, cancellation_token=cancel_token):
                steps.append(step)

        # 只有第一层 A 被执行（CancellationError 在第二层前抛出）
        assert len(steps) == 3  # 只有节点 A 的 3 个步骤

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """超时处理 - 节点执行超时被捕获"""
        node = PlanNode(id="slow", description="慢任务")
        plan = _make_plan({"slow": node})

        orch = _make_orchestrator()
        orch._max_timeout = 0.1  # 极短超时
        orch._get_or_create_agent = MagicMock(
            return_value=_SlowMockAgent(delay=5.0)
        )

        steps = []
        async for step in orch.execute_plan(plan):
            steps.append(step)

        # 超时后节点状态应为 FAILED
        assert node.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """并发数限制 - 信号量确保同时执行不超过 max_concurrency"""
        nodes = {
            f"n{i}": PlanNode(id=f"n{i}", description=f"任务{i}", dependencies=[])
            for i in range(5)
        }
        plan = _make_plan(nodes)

        orch = _make_orchestrator(max_concurrency=2)

        # 追踪同时执行的并发数
        concurrent_count = 0
        max_concurrent = 0

        class _CountingAgent(_MockAgentSteps):
            async def execute(self, task, context=None, cancellation_token=None):
                nonlocal concurrent_count, max_concurrent
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                try:
                    async for step in super().execute(task, context, cancellation_token):
                        yield step
                finally:
                    concurrent_count -= 1

        orch._get_or_create_agent = MagicMock(
            return_value=_CountingAgent()
        )

        steps = []
        async for step in orch.execute_plan(plan):
            steps.append(step)

        assert max_concurrent <= 2, f"最大并发 {max_concurrent} 超过限制 2"
        assert len(steps) == 15  # 5 nodes × 3 steps

    @pytest.mark.asyncio
    async def test_agent_reuse(self):
        """Agent 实例复用 - 同角色只创建一次"""
        node_a = PlanNode(id="A", description="任务A", assigned_role=AgentRole.RESEARCHER)
        node_b = PlanNode(id="B", description="任务B", assigned_role=AgentRole.RESEARCHER)
        plan = _make_plan({"A": node_a, "B": node_b})

        orch = _make_orchestrator()
        # 只 mock _get_or_create_agent，让它真实调用缓存的逻辑
        with patch.object(orch, "_get_or_create_agent", wraps=orch._get_or_create_agent) as mock_get:
            mock_agent = _MockAgentSteps(role=AgentRole.RESEARCHER)
            # 注入 agent 到缓存
            orch._agent_cache[AgentRole.RESEARCHER] = mock_agent

            steps = []
            async for step in orch.execute_plan(plan):
                steps.append(step)

            # _get_or_create_agent 应命中缓存，不创建新实例
            assert len(steps) == 6
            # 验证缓存被使用（Agent 来自缓存而非新建）
            assert orch._agent_cache.get(AgentRole.RESEARCHER) is mock_agent

    @pytest.mark.asyncio
    async def test_empty_plan(self):
        """空规划图不产出任何步骤"""
        orch = _make_orchestrator()
        plan = PlanGraph()

        steps = []
        async for step in orch.execute_plan(plan):
            steps.append(step)

        assert len(steps) == 0

    @pytest.mark.asyncio
    async def test_circular_plan_raises(self):
        """存在循环依赖的规划图执行时抛出 ValueError"""
        nodes = {
            "A": PlanNode(id="A", description="A", dependencies=["B"]),
            "B": PlanNode(id="B", description="B", dependencies=["A"]),
        }
        plan = _make_plan(nodes)
        orch = _make_orchestrator()

        with pytest.raises(ValueError, match="循环依赖"):
            async for _ in orch.execute_plan(plan):
                pass

    @pytest.mark.asyncio
    async def test_semaphore_min_concurrency(self):
        """max_concurrency < 1 时抛出 ValueError"""
        with pytest.raises(ValueError, match="必须 ≥ 1"):
            Orchestrator(llm_router=MagicMock(), tool_registry=ToolRegistry(), max_concurrency=0)

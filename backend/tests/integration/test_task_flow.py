"""
集成测试 - 完整任务执行流程

测试从任务创建到完成/取消的端到端流程，以及多 Agent 协作。
所有 LLM 调用均被 Mock，不依赖外部 API。
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_forge.agents.executor_agent import ExecutorAgent
from agent_forge.agents.factory import AgentFactory
from agent_forge.agents.researcher_agent import ResearcherAgent
from agent_forge.core.cancellation import CancellationError, CancellationToken
from agent_forge.core.llm_client import LLMResponse
from agent_forge.core.orchestrator import Orchestrator
from agent_forge.core.planner import PlanGraph, PlanNode, Planner
from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.models.schemas import AgentRole, AgentStep, StepType, Task, TaskStatus


# =============================================================================
# 辅助
# =============================================================================


def _make_router(plan_json: dict = None) -> MagicMock:
    """创建 Mock LLMRouter，返回规划 JSON 或默认响应"""
    router = MagicMock()
    if plan_json:
        content = json.dumps(plan_json)
    else:
        content = "mock response"

    router.route = AsyncMock(
        return_value=LLMResponse(content=content, model="moonshot-v1-8k")
    )
    return router


def _basic_plan_json() -> dict:
    """基本 DAG 规划：researcher → executor"""
    return {
        "tasks": [
            {
                "id": "task_1",
                "description": "研究分析需求",
                "dependencies": [],
                "estimated_duration": 30,
                "assigned_role": "researcher",
            },
            {
                "id": "task_2",
                "description": "执行方案",
                "dependencies": ["task_1"],
                "estimated_duration": 60,
                "assigned_role": "executor",
            },
        ],
        "root_task_id": "task_1",
    }


def _multi_agent_plan_json() -> dict:
    """多 Agent 协作 DAG：researcher + coder(并行) → executor"""
    return {
        "tasks": [
            {
                "id": "task_1",
                "description": "研究分析",
                "dependencies": [],
                "assigned_role": "researcher",
            },
            {
                "id": "task_2",
                "description": "编写代码",
                "dependencies": [],
                "assigned_role": "executor",
            },
            {
                "id": "task_3",
                "description": "集成测试",
                "dependencies": ["task_1", "task_2"],
                "assigned_role": "executor",
            },
        ],
        "root_task_id": "task_1",
    }


class _SimpleTestAgent:
    """最简测试 Agent，产出固定步骤"""

    def __init__(self, agent_id: str, role: AgentRole):
        self.agent_id = agent_id
        self.role = role
        self.state = MagicMock(status="idle")
        self.memory = []

    async def execute(self, task, context=None, cancellation_token=None):
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=1,
            step_type=StepType.THOUGHT,
            content=f"[{self.role.value}] 分析: {task.title}",
        )
        # 检查取消
        if cancellation_token:
            await cancellation_token.check_cancellation()
        yield AgentStep(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_role=self.role,
            step_number=2,
            step_type=StepType.FINAL,
            content=f"[{self.role.value}] 完成: {task.title}",
        )

    async def on_task_start(self, task):
        self.state.status = "busy"

    async def on_task_complete(self, task, result):
        self.state.status = "idle"

    async def on_task_error(self, task, error):
        self.state.status = "error"


# =============================================================================
# TestEndToEnd
# =============================================================================


class TestEndToEnd:
    """端到端任务流程测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_task(self):
        """完整流程：创建 → 规划 → 执行 → 完成"""
        # 1. 准备 LLM Router（Mock 返回规划 JSON）
        plan_data = _basic_plan_json()
        router = _make_router(plan_json=plan_data)

        # 2. Planner 生成 PlanGraph
        planner = Planner(llm_router=router)
        graph = await planner.plan("分析用户需求并执行方案")

        # 3. 验证规划结果
        assert len(graph.nodes) == 2
        assert graph.validate_no_cycles()

        # 4. 创建 Orchestrator 并注入 Mock Agent
        tool_registry = ToolRegistry()
        orch = Orchestrator(
            llm_router=router,
            tool_registry=tool_registry,
            max_concurrency=3,
        )
        orch._max_timeout = 5.0

        # 注入 Mock Agent（绕过 AgentFactory）
        orch._get_or_create_agent = MagicMock(
            return_value=_SimpleTestAgent(agent_id="test-agent", role=AgentRole.EXECUTOR)
        )

        # 5. 执行规划
        steps = []
        async for step in orch.execute_plan(graph):
            steps.append(step)

        # 6. 验证执行结果
        assert len(steps) == 4  # 2 节点 × 2 步骤
        assert all(isinstance(s, AgentStep) for s in steps)

        # 验证节点状态
        for node in graph.nodes.values():
            assert node.status == TaskStatus.COMPLETED, f"节点 {node.id} 应为 COMPLETED"

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self):
        """多 Agent 协作流程：并行执行 → 聚合"""
        plan_data = _multi_agent_plan_json()
        router = _make_router(plan_json=plan_data)

        # 规划
        planner = Planner(llm_router=router)
        graph = await planner.plan("多 Agent 协作任务")

        assert len(graph.nodes) == 3

        # 编排
        tool_registry = ToolRegistry()
        orch = Orchestrator(
            llm_router=router,
            tool_registry=tool_registry,
            max_concurrency=3,
        )
        orch._max_timeout = 5.0

        # 注入 Agent：模拟不同角色
        agent_map = {}

        def _get_or_create(role):
            if role not in agent_map:
                agent_map[role] = _SimpleTestAgent(
                    agent_id=f"agent-{role.value}", role=role
                )
            return agent_map[role]

        orch._get_or_create_agent = MagicMock(side_effect=_get_or_create)

        steps = []
        async for step in orch.execute_plan(graph):
            steps.append(step)

        # task_1 和 task_2 并行（第 1 层，共 2 步 × 2 节点 = 4 步）
        # task_3 依赖两者（第 2 层，2 步）
        assert len(steps) == 6, f"预期 6 步，实际 {len(steps)} 步"

        # 验证 Agent 复用：researcher 角色只创建一次
        assert len(agent_map) <= 2, "不同角色不应重复创建 Agent"

    @pytest.mark.asyncio
    async def test_cancel_flow(self):
        """取消流程：执行中被取消，后续节点不执行"""
        plan_data = _basic_plan_json()
        router = _make_router(plan_json=plan_data)

        planner = Planner(llm_router=router)
        graph = await planner.plan("取消测试任务")

        tool_registry = ToolRegistry()
        orch = Orchestrator(
            llm_router=router,
            tool_registry=tool_registry,
            max_concurrency=2,
        )
        orch._max_timeout = 5.0

        # 取消令牌
        cancel_token = CancellationToken()

        class _CancelOnSecondStep:
            """第二个步骤产出后取消"""

            def __init__(self):
                self.agent_id = "cancel-agent"
                self.role = AgentRole.EXECUTOR
                self.state = MagicMock(status="idle")

            async def execute(self, task, context=None, cancellation_token=None):
                yield AgentStep(
                    task_id=task.id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    step_number=1,
                    step_type=StepType.THOUGHT,
                    content="启动",
                )
                # 在第一个节点完成时取消
                await cancel_token.cancel("测试取消")
                # 取消后触发 CancellationError
                if cancellation_token:
                    await cancellation_token.check_cancellation()

            async def on_task_start(self, task):
                self.state.status = "busy"

            async def on_task_complete(self, task, result):
                self.state.status = "idle"

            async def on_task_error(self, task, error):
                self.state.status = "error"

        orch._get_or_create_agent = MagicMock(
            return_value=_CancelOnSecondStep()
        )

        steps = []
        # Orchestrator 内部捕获 CancellationError，不会传播到外层
        async for step in orch.execute_plan(graph, cancellation_token=cancel_token):
            steps.append(step)

        # task_1 执行中被取消，task_2 不应执行
        node_statuses = {nid: node.status for nid, node in graph.nodes.items()}
        assert node_statuses.get("task_1") == TaskStatus.CANCELLED, (
            f"task_1 应被取消，实际: {node_statuses}"
        )
        # task_2 应保持 PENDING（未被执行）
        assert node_statuses.get("task_2") == TaskStatus.PENDING, (
            f"task_2 应保持 PENDING，实际: {node_statuses}"
        )
        # 只收集到被取消节点的步骤
        assert len(steps) >= 1

    @pytest.mark.asyncio
    async def test_component_integration(self):
        """组件集成测试：Planner → Orchestrator 完整数据流"""
        plan_data = _basic_plan_json()
        router = _make_router(plan_json=plan_data)

        # ---- Planner 阶段 ----
        planner = Planner(llm_router=router)
        graph = await planner.plan("端到端集成测试")

        assert graph.validate_no_cycles()
        layers = graph.get_execution_order()
        assert len(layers) == 2, "基本 DAG 应为 2 层"

        # ---- Orchestrator 阶段 ----
        orch = Orchestrator(
            llm_router=router,
            tool_registry=ToolRegistry(),
            max_concurrency=2,
        )
        orch._max_timeout = 5.0

        collected = []
        orch._get_or_create_agent = MagicMock(
            return_value=_SimpleTestAgent(agent_id="int-agent", role=AgentRole.EXECUTOR)
        )

        async for step in orch.execute_plan(graph):
            collected.append(step)

        # 验证步骤完整性
        step_types = [s.step_type for s in collected]
        assert StepType.THOUGHT in step_types
        assert StepType.FINAL in step_types

        # 验证任务结果通过 Aggregate
        for nid, node in graph.nodes.items():
            assert node.status == TaskStatus.COMPLETED, f"节点 {nid} 未完成"


# =============================================================================
# TestPipelineEdgeCases
# =============================================================================


class TestPipelineEdgeCases:
    """管道边界情况测试"""

    @pytest.mark.asyncio
    async def test_single_node_pipeline(self):
        """单节点管道直接完成"""
        plan_data = {
            "tasks": [
                {
                    "id": "only_task",
                    "description": "唯一任务",
                    "dependencies": [],
                    "assigned_role": "executor",
                }
            ],
            "root_task_id": "only_task",
        }
        router = _make_router(plan_json=plan_data)
        planner = Planner(llm_router=router)
        graph = await planner.plan("单一任务")

        orch = Orchestrator(llm_router=router, tool_registry=ToolRegistry())
        orch._max_timeout = 5.0
        orch._get_or_create_agent = MagicMock(
            return_value=_SimpleTestAgent(agent_id="solo", role=AgentRole.EXECUTOR)
        )

        steps = []
        async for step in orch.execute_plan(graph):
            steps.append(step)

        assert len(steps) == 2  # thought + final
        assert graph.nodes["only_task"].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """节点异常不影响同层其他节点"""
        plan_data = {
            "tasks": [
                {
                    "id": "good_task",
                    "description": "正常任务",
                    "dependencies": [],
                    "assigned_role": "executor",
                },
                {
                    "id": "bad_task",
                    "description": "会失败的任务",
                    "dependencies": [],
                    "assigned_role": "researcher",  # 不同角色，确保不同 Agent 实例
                },
            ],
            "root_task_id": "good_task",
        }
        router = _make_router(plan_json=plan_data)
        planner = Planner(llm_router=router)
        graph = await planner.plan("容错测试")

        orch = Orchestrator(llm_router=router, tool_registry=ToolRegistry())
        orch._max_timeout = 5.0

        # 正常 agent
        good_agent = _SimpleTestAgent(agent_id="good", role=AgentRole.EXECUTOR)

        class _FailingAgent:
            def __init__(self):
                self.agent_id = "bad"
                self.role = AgentRole.RESEARCHER
                self.state = MagicMock(status="idle")

            async def execute(self, task, context=None, cancellation_token=None):
                raise RuntimeError("模拟执行异常")

            async def on_task_start(self, task):
                self.state.status = "busy"

            async def on_task_complete(self, task, result):
                pass

            async def on_task_error(self, task, error):
                self.state.status = "error"

        def _side_effect(role):
            if role == AgentRole.RESEARCHER:
                return _FailingAgent()
            return good_agent

        orch._get_or_create_agent = MagicMock(side_effect=_side_effect)

        steps = []
        async for step in orch.execute_plan(graph):
            steps.append(step)

        # good_task 应完成
        assert graph.nodes["good_task"].status == TaskStatus.COMPLETED
        # bad_task 应失败
        assert graph.nodes["bad_task"].status == TaskStatus.FAILED

"""
任务规划器模块测试

测试 Planner 的 JSON 解析策略、PlanGraph 拓扑排序和循环依赖检测。
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_forge.core.error_handler import ValidationException
from agent_forge.core.llm_client import LLMResponse
from agent_forge.core.planner import PlanGraph, PlanNode, Planner
from agent_forge.models.schemas import AgentRole, TaskStatus


# =============================================================================
# 辅助函数
# =============================================================================


def _make_llm_router(content: str, model: str = "test-model") -> MagicMock:
    """创建 Mock LLMRouter，返回指定内容的 LLMResponse"""
    router = MagicMock()
    router.route = AsyncMock(
        return_value=LLMResponse(content=content, model=model)
    )
    return router


def _make_strict_json_plan() -> dict:
    """生成标准严格 JSON 规划数据"""
    return {
        "tasks": [
            {
                "id": "task_1",
                "description": "分析用户需求",
                "dependencies": [],
                "estimated_duration": 30,
                "assigned_role": "researcher",
            },
            {
                "id": "task_2",
                "description": "编写核心代码",
                "dependencies": ["task_1"],
                "estimated_duration": 60,
                "assigned_role": "coder",
            },
            {
                "id": "task_3",
                "description": "测试和验证",
                "dependencies": ["task_2"],
                "estimated_duration": 45,
                "assigned_role": "executor",
            },
        ],
        "root_task_id": "task_1",
    }


# =============================================================================
# TestPlanGraph - 规划图基础
# =============================================================================


class TestPlanGraph:
    """测试 PlanGraph 拓扑排序与循环检测"""

    def test_get_execution_order_linear(self):
        """测试线性 DAG 的拓扑排序"""
        nodes = {
            "A": PlanNode(id="A", description="任务A", dependencies=[]),
            "B": PlanNode(id="B", description="任务B", dependencies=["A"]),
            "C": PlanNode(id="C", description="任务C", dependencies=["B"]),
        }
        graph = PlanGraph(nodes=nodes, root_node_id="A")
        order = graph.get_execution_order()

        assert len(order) == 3, "线性 DAG 应为 3 层"
        assert order[0] == ["A"]
        assert order[1] == ["B"]
        assert order[2] == ["C"]

    def test_get_execution_order_parallel(self):
        """测试并行层（多个节点无相互依赖）"""
        nodes = {
            "A": PlanNode(id="A", description="根任务", dependencies=[]),
            "B": PlanNode(id="B", description="并行B", dependencies=["A"]),
            "C": PlanNode(id="C", description="并行C", dependencies=["A"]),
        }
        graph = PlanGraph(nodes=nodes, root_node_id="A")
        order = graph.get_execution_order()

        assert len(order) == 2, "应产生 2 层"
        assert order[0] == ["A"]
        # 同层排序按 ID 确定性排列
        assert order[1] == ["B", "C"]

    def test_get_execution_order_diamond(self):
        """测试菱形依赖 DAG"""
        nodes = {
            "A": PlanNode(id="A", description="起点", dependencies=[]),
            "B": PlanNode(id="B", description="分支B", dependencies=["A"]),
            "C": PlanNode(id="C", description="分支C", dependencies=["A"]),
            "D": PlanNode(id="D", description="汇合", dependencies=["B", "C"]),
        }
        graph = PlanGraph(nodes=nodes, root_node_id="A")
        order = graph.get_execution_order()

        assert len(order) == 3
        assert order[0] == ["A"]
        assert set(order[1]) == {"B", "C"}
        assert order[2] == ["D"]

    def test_get_execution_order_empty(self):
        """测试空图返回空列表"""
        graph = PlanGraph()
        assert graph.get_execution_order() == []

    def test_circular_dependency_detected(self):
        """测试循环依赖被正确检测"""
        nodes = {
            "A": PlanNode(id="A", description="任务A", dependencies=["B"]),
            "B": PlanNode(id="B", description="任务B", dependencies=["A"]),
        }
        graph = PlanGraph(nodes=nodes)
        assert not graph.validate_no_cycles(), "应检测到循环依赖"

        # get_execution_order 也应抛出异常
        with pytest.raises(ValueError, match="循环依赖"):
            graph.get_execution_order()

    def test_self_loop_detected(self):
        """测试自环检测"""
        nodes = {
            "A": PlanNode(id="A", description="自环任务", dependencies=["A"]),
        }
        graph = PlanGraph(nodes=nodes)
        assert not graph.validate_no_cycles()

    def test_validate_no_cycles_clean(self):
        """测试无环图通过验证"""
        nodes = {
            "A": PlanNode(id="A", description="任务A", dependencies=[]),
            "B": PlanNode(id="B", description="任务B", dependencies=["A"]),
        }
        graph = PlanGraph(nodes=nodes)
        assert graph.validate_no_cycles()

    def test_get_node(self):
        """测试 get_node 查询"""
        node = PlanNode(id="x", description="节点X")
        graph = PlanGraph(nodes={"x": node})
        assert graph.get_node("x") is node
        assert graph.get_node("not_exist") is None

    def test_dependency_to_nonexistent(self):
        """测试依赖不存在的节点不影响拓扑排序"""
        nodes = {
            "A": PlanNode(id="A", description="任务A", dependencies=["ghost"]),
            "B": PlanNode(id="B", description="任务B", dependencies=[]),
        }
        graph = PlanGraph(nodes=nodes)
        order = graph.get_execution_order()
        # A 依赖的 ghost 不在图中，入度为 0；B 也无依赖
        assert len(order) == 1, "两个节点都无有效依赖，应在同一层"
        assert set(order[0]) == {"A", "B"}


# =============================================================================
# TestPlanner - 规划器（LLM 响应解析）
# =============================================================================


class TestPlanner:
    """测试 Planner 的三层解析策略"""

    @pytest.fixture
    def planner(self):
        """创建 Planner 实例（不依赖真实 LLM）"""
        return Planner(llm_router=MagicMock())

    # ------------------------------------------------------------------
    # 严格 JSON 解析
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_plan_strict_json(self, planner):
        """LLM 返回严格 JSON 格式时正确解析"""
        data = _make_strict_json_plan()
        content = json.dumps(data)
        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("分析用户需求并编写代码")

        assert len(graph.nodes) == 3
        assert graph.root_node_id == "task_1"
        assert "task_1" in graph.nodes
        assert "task_2" in graph.nodes
        assert "task_3" in graph.nodes

        node1 = graph.nodes["task_1"]
        assert node1.description == "分析用户需求"
        assert node1.assigned_role == AgentRole.RESEARCHER
        assert node1.dependencies == []

        node2 = graph.nodes["task_2"]
        assert node2.dependencies == ["task_1"]

    @pytest.mark.asyncio
    async def test_plan_loose_json_code_fence(self, planner):
        """LLM 返回 ```json ... ``` 包裹的宽松 JSON"""
        data = _make_strict_json_plan()
        content = f"好的，以下是任务规划：\n```json\n{json.dumps(data)}\n```\n请确认。"

        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("分析用户需求并编写代码")
        assert len(graph.nodes) == 3
        assert graph.root_node_id == "task_1"

    @pytest.mark.asyncio
    async def test_plan_loose_json_no_annotation(self, planner):
        """LLM 返回 ``` ... ``` 无标注代码块"""
        data = _make_strict_json_plan()
        content = f"规划如下：\n```\n{json.dumps(data)}\n```"

        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("分析用户需求并编写代码")
        assert len(graph.nodes) == 3

    @pytest.mark.asyncio
    async def test_plan_loose_json_inline_object(self, planner):
        """LLM 返回嵌入文本中的 JSON 对象（无代码块）"""
        data = _make_strict_json_plan()
        content = f"这是规划结果，{json.dumps(data)}，可以开始执行了。"

        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("分析用户需求并编写代码")
        assert len(graph.nodes) == 3

    # ------------------------------------------------------------------
    # 回退单任务
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_plan_fallback_single_task(self, planner):
        """无法解析 JSON 时回退到单任务模式（回退使用 LLM 响应内容作为节点描述）"""
        content = "这是一个复杂的任务，我无法拆解它。建议直接执行。"
        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("无法拆解的任务")

        assert len(graph.nodes) == 1
        node = list(graph.nodes.values())[0]
        # 回退模式将 LLM 响应文本作为节点描述
        assert node.description == content
        assert node.dependencies == []
        assert node.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_plan_fallback_invalid_json(self, planner):
        """JSON 格式错误时回退到单任务"""
        content = '{"tasks": [invalid json here}'
        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("某个任务描述")
        assert len(graph.nodes) == 1

    # ------------------------------------------------------------------
    # 循环依赖
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_plan_circular_dependency(self, planner):
        """LLM 产出的规划包含循环依赖时抛出异常"""
        circular_plan = {
            "tasks": [
                {
                    "id": "task_1",
                    "description": "任务1",
                    "dependencies": ["task_2"],
                },
                {
                    "id": "task_2",
                    "description": "任务2",
                    "dependencies": ["task_1"],
                },
            ],
            "root_task_id": "task_1",
        }
        content = json.dumps(circular_plan)
        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        with pytest.raises(ValidationException, match="循环依赖"):
            await planner.plan("循环任务")

    # ------------------------------------------------------------------
    # 空任务
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_task_still_usable(self, planner):
        """空任务描述不导致崩溃"""
        content = json.dumps({
            "tasks": [
                {
                    "id": "empty_task",
                    "description": "",
                    "dependencies": [],
                }
            ],
            "root_task_id": "empty_task",
        })
        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("")
        assert len(graph.nodes) == 1

    @pytest.mark.asyncio
    async def test_empty_task_fallback(self, planner):
        """LLM 返回空 tasks 数组时回退到单任务"""
        content = json.dumps({"tasks": [], "root_task_id": ""})
        planner.llm_router.route = AsyncMock(
            return_value=LLMResponse(content=content, model="moonshot-v1-8k")
        )

        graph = await planner.plan("某个任务")
        # 空 tasks → 宽松解析也失败 → 回退单任务
        assert len(graph.nodes) == 1

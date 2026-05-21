"""
AgentForge 任务编排器模块

按 PlanGraph 的依赖图调度 Agent 执行。
层内节点并行（受信号量控制），层间串行保证依赖关系。
每个节点独立超时 120 秒，全程支持 CancellationToken 取消。
"""
import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from agent_forge.agents.base import BaseAgent
from agent_forge.agents.factory import AgentFactory
from agent_forge.core.cancellation import CancellationError, CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.core.planner import PlanGraph, PlanNode
from agent_forge.core.reflection_engine import ReflectionEngine
from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.models.schemas import (
    AgentRole,
    AgentStep,
    StepType,
    Task,
    TaskResult,
    TaskStatus,
)
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 120  # 秒
DEFAULT_MAX_CONCURRENCY = 3


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class Orchestrator:
    """任务编排器

    按 PlanGraph 的拓扑分层结构调度 Agent 执行：

    - 调用 ``PlanGraph.get_execution_order()`` 获取分层执行序列
    - 层内节点通过 ``asyncio.gather`` 并行执行
    - 并发数由 ``asyncio.Semaphore`` 控制在 max_concurrency 以内
    - 每个节点默认超时 120 秒（DEFAULT_TIMEOUT）
    - 每层开始前、每个节点 step 产出后检查 CancellationToken
    - 失败/取消的节点状态会写回 PlanNode，其余节点继续执行

    用法::

        orchestrator = Orchestrator(llm_router, tool_registry, max_concurrency=3)
        async for step in orchestrator.execute_plan(plan, cancel_token):
            yield step  # 实时推送进度到前端/日志
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        reflection_engine: Optional[ReflectionEngine] = None,
    ) -> None:
        """
        Args:
            llm_router: LLM 路由器，供创建的 Agent 使用
            tool_registry: 工具注册中心（预留，后续可注入给 Agent）
            max_concurrency: 同层最大并行 Agent 数（≥1）
            reflection_engine: 可选的反思引擎，执行完成后自动生成反思报告
        """
        self.llm_router = llm_router
        self.tool_registry = tool_registry
        if max_concurrency < 1:
            raise ValueError(f"max_concurrency 必须 ≥ 1，当前值: {max_concurrency}")
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._agent_cache: Dict[AgentRole, BaseAgent] = {}
        self._max_timeout = DEFAULT_TIMEOUT
        self.reflection_engine = reflection_engine

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def execute_plan(
        self,
        plan: PlanGraph,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行完整规划图，逐层调度并按需产出执行步骤

        Args:
            plan: 已通过 Planner 生成的 PlanGraph
            cancellation_token: 可选取消令牌；被取消时立即停止后续层

        Yields:
            AgentStep – 每个完成节点的所有步骤（按节点聚合，节点间无序）
        """
        if not plan.nodes:
            logger.warning("规划图为空，无任务可执行")
            return

        # 预校验：循环依赖不可执行
        if not plan.validate_no_cycles():
            raise ValueError("规划图存在循环依赖，无法执行")

        layers = plan.get_execution_order()
        logger.info(
            "开始执行规划：%d 层，%d 个节点",
            len(layers),
            len(plan.nodes),
        )

        # 收集所有步骤和结果，用于执行后反思
        all_steps: List[AgentStep] = []
        all_results: List[TaskResult] = []

        for layer_idx, layer in enumerate(layers):
            # --- 层间取消检查 ---
            if cancellation_token is not None:
                await cancellation_token.check_cancellation()

            logger.info(
                "第 %d/%d 层，节点: %s",
                layer_idx + 1,
                len(layers),
                layer,
            )

            results_and_steps = await self._execute_layer(
                layer, plan, cancellation_token
            )

            # 产出步骤（逐层输出，保证上层完成后再出下层）
            for result, steps in results_and_steps:
                all_results.append(result)
                all_steps.extend(steps)
                for step in steps:
                    yield step

            # 终止语义：一旦出现取消，不再执行后续层
            if any(
                r.status == TaskStatus.CANCELLED
                for r, _ in results_and_steps
            ):
                logger.warning("检测到取消状态，终止后续层执行")
                return

        # ------------------------------------------------------------------
        # 执行后反思（不影响主流程）
        # ------------------------------------------------------------------
        if self.reflection_engine is not None and all_steps:
            try:
                # 确定主 Agent 角色（取第一个节点的分配角色）
                primary_role = AgentRole.EXECUTOR
                primary_id = "orchestrator"
                first_node_id = None
                for layer in layers:
                    if layer:
                        first_node_id = layer[0]
                        break
                if first_node_id and first_node_id in plan.nodes:
                    node = plan.nodes[first_node_id]
                    primary_role = node.assigned_role or AgentRole.EXECUTOR
                    # 尝试从缓存获取 Agent ID
                    cached = self._agent_cache.get(primary_role)
                    if cached is not None:
                        primary_id = cached.agent_id

                # 聚合整体结果
                any_failed = any(
                    r.status in (TaskStatus.FAILED, TaskStatus.CANCELLED)
                    for r in all_results
                )
                overall_status = (
                    TaskStatus.FAILED if any_failed else TaskStatus.COMPLETED
                )
                overall_result = TaskResult(
                    task_id=plan.root_node_id
                    or next(iter(plan.nodes), "unknown"),
                    status=overall_status,
                    output="\n".join(
                        r.output or "" for r in all_results if r.output
                    ),
                    steps_count=len(all_steps),
                )

                report = await self.reflection_engine.reflect(
                    task_id=overall_result.task_id,
                    agent_id=primary_id,
                    agent_role=primary_role,
                    steps=all_steps,
                    result=overall_result,
                )
                logger.info("反思报告生成: %s", report.summary[:80])

                # 将反思报告作为最终步骤 yield
                yield AgentStep(
                    task_id=overall_result.task_id,
                    agent_id="reflection",
                    agent_role=AgentRole.EXECUTOR,
                    step_number=len(all_steps) + 1,
                    step_type=StepType.FINAL,
                    content=(
                        f"反思报告: {report.summary}\n\n"
                        f"**优点**: {', '.join(report.strengths) if report.strengths else '无'}\n\n"
                        f"**改进**: {', '.join(report.suggestions) if report.suggestions else '无'}\n\n"
                        f"**学到**: {report.learned}"
                    ),
                )
            except Exception as e:
                logger.error("反思过程出错（不影响主流程）: %s", e)

        logger.info("规划执行完毕")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _execute_node(
        self,
        node: PlanNode,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Tuple[TaskResult, List[AgentStep]]:
        """执行单个 PlanNode，返回结果与步骤列表

        内部流程:
        1. 获取/创建对应角色的 Agent（缓存复用）
        2. 构造 Task 对象
        3. 带超时执行 agent.execute()，逐步骤收集
        4. 捕获超时/取消/异常，返回对应 TaskResult

        Args:
            node: 规划图中的任务节点
            cancellation_token: 取消令牌

        Returns:
            (TaskResult, [AgentStep, ...]) – 结果与已收集的全部步骤
        """
        role = node.assigned_role or AgentRole.EXECUTOR
        agent = self._get_or_create_agent(role)

        task = Task(
            id=node.id,
            title=node.description[:80],
            description=node.description,
            status=TaskStatus.EXECUTING,
        )

        node.status = TaskStatus.EXECUTING
        steps: List[AgentStep] = []

        # --- 执行体：收集 Agent 产出的每一步 ---
        async def _run_agent() -> None:
            async for step in agent.execute(
                task=task,
                context=None,
                cancellation_token=cancellation_token,
            ):
                # 步骤间取消检查（Agent 内部也有检查，此处兜底）
                if cancellation_token is not None:
                    await cancellation_token.check_cancellation()
                steps.append(step)

        try:
            await agent.on_task_start(task)

            # 超时控制
            await asyncio.wait_for(_run_agent(), timeout=self._max_timeout)

            result = TaskResult(
                task_id=node.id,
                status=TaskStatus.COMPLETED,
                output=self._aggregate_output(steps),
                steps_count=len(steps),
            )
            node.status = TaskStatus.COMPLETED
            await agent.on_task_complete(task, result)

        except asyncio.TimeoutError:
            logger.error("节点 %s 执行超时 (%ds)", node.id, self._max_timeout)
            result = TaskResult(
                task_id=node.id,
                status=TaskStatus.FAILED,
                error_message=f"执行超时 ({self._max_timeout} 秒)",
                steps_count=len(steps),
            )
            node.status = TaskStatus.FAILED
            await agent.on_task_error(task, asyncio.TimeoutError("执行超时"))

        except CancellationError as e:
            logger.warning("节点 %s 被取消: %s", node.id, e)
            result = TaskResult(
                task_id=node.id,
                status=TaskStatus.CANCELLED,
                error_message=str(e),
                steps_count=len(steps),
            )
            node.status = TaskStatus.CANCELLED
            await agent.on_task_error(task, e)

        except Exception as e:
            logger.exception("节点 %s 执行异常", node.id)
            result = TaskResult(
                task_id=node.id,
                status=TaskStatus.FAILED,
                error_message=str(e),
                steps_count=len(steps),
            )
            node.status = TaskStatus.FAILED
            await agent.on_task_error(task, e)

        return result, steps

    async def _execute_layer(
        self,
        layer: List[str],
        plan: PlanGraph,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> List[Tuple[TaskResult, List[AgentStep]]]:
        """并行执行一层中的所有节点

        每个节点执行前获取信号量，确保并发数不超过 ``max_concurrency``。
        使用 ``asyncio.gather(return_exceptions=True)`` 防止单节点异常
        中断整层。

        Args:
            layer: 本层节点 ID 列表
            plan: 规划图（用于 get_node 查询）
            cancellation_token: 取消令牌

        Returns:
            (TaskResult, steps) 元组列表，与 layer 顺序一一对应
        """

        async def _guarded_execute(node_id: str) -> Tuple[TaskResult, List[AgentStep]]:
            """信号量保护的单节点执行"""
            async with self._semaphore:
                node = plan.get_node(node_id)
                if node is None:
                    logger.error("节点 %s 不在规划图中", node_id)
                    return (
                        TaskResult(
                            task_id=node_id,
                            status=TaskStatus.FAILED,
                            error_message=f"节点 {node_id} 不存在于规划图中",
                        ),
                        [],
                    )
                return await self._execute_node(node, cancellation_token)

        # 并发执行，异常转为返回值
        coros = [_guarded_execute(nid) for nid in layer]
        gathered = await asyncio.gather(*coros, return_exceptions=True)

        # 兜底：把未捕获的异常包装为失败结果
        processed: List[Tuple[TaskResult, List[AgentStep]]] = []
        for idx, item in enumerate(gathered):
            if isinstance(item, Exception):
                node_id = layer[idx]
                logger.exception("层内节点 %s 抛出未捕获异常", node_id)
                processed.append((
                    TaskResult(
                        task_id=node_id,
                        status=TaskStatus.FAILED,
                        error_message=str(item),
                    ),
                    [],
                ))
            else:
                processed.append(item)

        return processed

    def _get_or_create_agent(self, role: AgentRole) -> BaseAgent:
        """按角色获取 Agent 实例（懒加载 + 缓存）

        Agent 实例按角色缓存，同一角色在整个编排过程中复用。
        调用 ``AgentFactory.create(role, llm_router)`` 创建实例。

        Args:
            role: Agent 角色枚举

        Returns:
            BaseAgent 子类实例

        Raises:
            ValueError: 角色未在 AgentFactory 注册时
        """
        if role not in self._agent_cache:
            agent = AgentFactory.create(role, self.llm_router)
            self._agent_cache[role] = agent
            logger.info("创建 Agent 实例并缓存: %s", role.value)
        return self._agent_cache[role]

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_output(steps: List[AgentStep]) -> str:
        """从步骤列表中提取最终输出

        优先取最后一个 StepType.FINAL 步骤的内容；
        如果没有，拼接所有有内容的步骤（用换行符分隔）。

        Args:
            steps: 执行步骤列表

        Returns:
            聚合后的文本输出
        """
        if not steps:
            return ""

        # 优先：最后一个 FINAL 步骤
        for step in reversed(steps):
            if step.step_type == StepType.FINAL:
                return step.content

        # 回退：拼接所有非空步骤内容
        return "\n".join(s.content for s in steps if s.content)

    def clear_agent_cache(self) -> None:
        """清空 Agent 实例缓存

        需要在同一编排器中切换不同 LLM 配置时调用。
        """
        self._agent_cache.clear()
        logger.info("Agent 缓存已清空")

"""
AgentForge 任务规划器模块

将自然语言任务描述拆解为结构化的子任务依赖图（DAG），
支持拓扑排序、并行执行层划分和循环依赖检测。
"""
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent_forge.core.error_handler import LLMException, ValidationException
from agent_forge.core.llm_client import LLMResponse, LLMRouter
from agent_forge.models.schemas import AgentRole, TaskStatus
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PlanNode:
    """规划图中的任务节点

    表示一个可分配给 Agent 执行的原子子任务。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: Optional[int] = None
    assigned_role: Optional[AgentRole] = None
    status: TaskStatus = TaskStatus.PENDING


class PlanGraph:
    """任务规划有向无环图（DAG）

    管理一组 PlanNode 及其依赖关系，提供拓扑排序、
    循环检测和节点查询功能。
    """

    def __init__(self, nodes: Optional[Dict[str, PlanNode]] = None, root_node_id: str = ""):
        """
        Args:
            nodes: 节点字典，key 为节点 ID
            root_node_id: 根节点 ID（无依赖的起始节点）
        """
        self.nodes: Dict[str, PlanNode] = nodes or {}
        self.root_node_id: str = root_node_id

    def get_execution_order(self) -> List[List[str]]:
        """拓扑排序，返回分层执行顺序（同层节点可并行执行）

        使用 BFS 层次的 Kahn 算法：
        - 计算每个节点的入度（未满足的依赖数）
        - 每一层包含所有入度为 0 的节点
        - 移除该层节点后，更新其余节点的入度

        Returns:
            嵌套列表，每层为可并行执行的节点 ID 列表

        Raises:
            ValueError: 图中存在循环依赖时抛出
        """
        if not self.nodes:
            return []

        # 计算入度：只统计实际存在于 nodes 中的依赖
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        reverse_deps: Dict[str, List[str]] = {nid: [] for nid in self.nodes}

        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                if dep in self.nodes:
                    in_degree[nid] += 1
                    reverse_deps.setdefault(dep, []).append(nid)

        # BFS 分层
        layers: List[List[str]] = []
        # 第一层：入度为 0 的节点
        current_layer = [nid for nid, deg in in_degree.items() if deg == 0]

        while current_layer:
            # 同层按 ID 排序，保证确定性
            current_layer.sort()
            layers.append(current_layer)
            next_layer: List[str] = []

            for nid in current_layer:
                for dependent in reverse_deps.get(nid, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_layer.append(dependent)

            current_layer = next_layer

        # 检查是否所有节点都已被处理
        total_processed = sum(len(layer) for layer in layers)
        if total_processed != len(self.nodes):
            remaining = set(self.nodes.keys()) - {
                nid for layer in layers for nid in layer
            }
            raise ValueError(
                f"图中存在循环依赖，无法完成拓扑排序。"
                f"未处理节点: {remaining}"
            )

        return layers

    def validate_no_cycles(self) -> bool:
        """检测图中是否存在循环依赖

        使用三色标记 DFS：
        - WHITE (0): 未访问
        - GRAY (1): 正在访问（递归栈中）
        - BLACK (2): 已完成

        Returns:
            True 表示无环，False 表示存在循环依赖
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self.nodes}

        cycle_nodes: List[str] = []

        def dfs(nid: str) -> bool:
            """DFS 遍历，返回 True 表示发现环"""
            color[nid] = GRAY
            node = self.nodes.get(nid)
            if node:
                for dep in node.dependencies:
                    if dep not in color:
                        # 依赖节点不在图中，跳过
                        continue
                    if color[dep] == GRAY:
                        cycle_nodes.append(dep)
                        return True
                    if color[dep] == WHITE:
                        if dfs(dep):
                            return True
            color[nid] = BLACK
            return False

        for nid in self.nodes:
            if color[nid] == WHITE:
                if dfs(nid):
                    logger.warning(f"检测到循环依赖，涉及节点: {cycle_nodes}")
                    return False

        return True

    def get_node(self, node_id: str) -> Optional[PlanNode]:
        """根据 ID 获取节点

        Args:
            node_id: 节点 ID

        Returns:
            PlanNode 实例或 None
        """
        return self.nodes.get(node_id)


class Planner:
    """任务规划器

    使用 LLM 将自然语言任务描述拆解为结构化的子任务依赖图，
    支持多层 JSON 解析策略和回退机制。
    """

    # 规划提示模板
    PLANNING_PROMPT_TEMPLATE = """你是一个专业的任务规划专家。请将以下任务拆解为可直接执行的子任务。

## 任务描述
{task}

## 可用 Agent 角色
{roles}

## 输出要求
请严格按照以下 JSON 格式输出子任务列表（不要输出其他内容）：
```json
{{
    "tasks": [
        {{
            "id": "task_1",
            "description": "子任务的具体描述，清晰明确",
            "dependencies": ["task_2"],
            "estimated_duration": 60,
            "assigned_role": "researcher"
        }}
    ],
    "root_task_id": "task_1"
}}
```

## 规划原则
1. 每个子任务应满足: 原子性（不可再分）、可分配性（可由单一Agent完成）、可验证性（有明确产出）
2. 依赖关系应形成 DAG（有向无环图），第一个节点（无依赖）为根任务
3. 合理估计每个子任务的耗时（分钟），合理分配 Agent 角色
4. 子任务数量控制在 3-10 个，避免过度拆分或拆分不足
5. dependencies 列表为空表示该任务没有前置依赖

请开始规划："""

    def __init__(self, llm_router: LLMRouter):
        """
        Args:
            llm_router: LLM 路由器实例，用于调用 LLM 进行任务规划
        """
        self.llm_router = llm_router

    async def plan(self, task_description: str) -> PlanGraph:
        """主入口：将自然语言任务拆解为 PlanGraph

        Args:
            task_description: 自然语言任务描述

        Returns:
            PlanGraph 实例，包含子任务节点和依赖关系

        Raises:
            LLMException: LLM 调用失败时抛出
            ValidationException: 生成的规划存在循环依赖时抛出
        """
        logger.info(f"开始规划任务: {task_description[:100]}...")

        # 1. 构建提示
        prompt = self._build_prompt(task_description)

        # 2. 调用 LLM
        try:
            response: LLMResponse = await self.llm_router.route(
                messages=[{"role": "user", "content": prompt}],
                complexity="medium",
            )
            logger.info(
                f"LLM 规划完成，模型: {response.model}，"
                f"耗时: {response.latency_ms}ms，"
                f"token 用量: {response.usage.get('total_tokens', 0)}"
            )
        except LLMException:
            raise
        except Exception as e:
            logger.error(f"LLM 调用异常: {e}")
            raise LLMException(f"LLM 规划调用失败: {str(e)}")

        # 3. 解析响应
        graph = self._parse_plan_response(response.content)

        # 4. 验证 DAG
        self._validate_dag(graph)

        logger.info(
            f"规划图构建完成，共 {len(graph.nodes)} 个节点，"
            f"根节点: {graph.root_node_id}"
        )
        return graph

    def _build_prompt(self, task: str) -> str:
        """构建规划提示模板

        Args:
            task: 任务描述

        Returns:
            格式化后的提示字符串
        """
        roles_desc = "\n".join(
            f"- {role.value}: {self._role_description(role)}"
            for role in AgentRole
        )
        return self.PLANNING_PROMPT_TEMPLATE.format(task=task, roles=roles_desc)

    @staticmethod
    def _role_description(role: AgentRole) -> str:
        """获取 Agent 角色描述"""
        descriptions = {
            AgentRole.PLANNER: "负责任务拆解和规划",
            AgentRole.RESEARCHER: "负责信息检索和调研分析",
            AgentRole.CODER: "负责代码编写和调试",
            AgentRole.WRITER: "负责文档撰写和内容创作",
            AgentRole.REVIEWER: "负责代码审查和质量保证",
            AgentRole.EXECUTOR: "负责任务执行和工具调用",
        }
        return descriptions.get(role, "通用任务执行")

    def _parse_plan_response(self, content: str) -> PlanGraph:
        """3 层解析策略：严格 JSON → 宽松 JSON → 回退单任务

        Args:
            content: LLM 响应的原始文本

        Returns:
            PlanGraph 实例
        """
        # 第 1 层：严格 JSON 解析
        result = self._parse_strict_json(content)
        if result:
            logger.info("使用严格 JSON 解析成功")
            return result

        # 第 2 层：宽松 JSON 解析（正则提取）
        result = self._parse_loose_json(content)
        if result:
            logger.info("使用宽松 JSON 解析成功")
            return result

        # 第 3 层：回退到单任务模式
        logger.warning(
            "所有 JSON 解析策略失败，回退到单任务模式"
        )
        return self._fallback_single_task(content)

    def _parse_strict_json(self, content: str) -> Optional[PlanGraph]:
        """严格 JSON 解析：直接 json.loads

        Args:
            content: LLM 原始响应文本

        Returns:
            PlanGraph 或 None（解析失败）
        """
        try:
            data = json.loads(content)
            return self._build_graph_from_data(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"严格 JSON 解析失败: {e}")
            return None

    def _parse_loose_json(self, content: str) -> Optional[PlanGraph]:
        """宽松 JSON 解析：用正则从文本中提取 JSON 块

        按优先级尝试:
        1. ```json ... ``` 代码块
        2. ``` ... ``` 无标注代码块
        3. 首个完整 JSON 对象 { ... }

        Args:
            content: LLM 原始响应文本

        Returns:
            PlanGraph 或 None（解析失败）
        """
        # 策略 1: 匹配 ```json ... ``` 代码块
        json_block_pattern = r"```json\s*\n?(.*?)\n?```"
        matches = re.findall(json_block_pattern, content, re.DOTALL)
        for match in matches:
            result = self._try_parse_json(match.strip())
            if result:
                return result

        # 策略 2: 匹配 ``` ... ``` 无标注代码块
        any_block_pattern = r"```\s*\n?(.*?)\n?```"
        matches = re.findall(any_block_pattern, content, re.DOTALL)
        for match in matches:
            result = self._try_parse_json(match.strip())
            if result:
                return result

        # 策略 3: 提取首个完整 JSON 对象
        brace_depth = 0
        start_idx = -1
        for i, ch in enumerate(content):
            if ch == "{":
                if brace_depth == 0:
                    start_idx = i
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth == 0 and start_idx >= 0:
                    json_str = content[start_idx : i + 1]
                    result = self._try_parse_json(json_str)
                    if result:
                        return result
                    start_idx = -1

        return None

    def _try_parse_json(self, json_str: str) -> Optional[PlanGraph]:
        """尝试解析 JSON 字符串并构建 PlanGraph

        Args:
            json_str: JSON 字符串

        Returns:
            PlanGraph 或 None
        """
        try:
            data = json.loads(json_str)
            return self._build_graph_from_data(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"JSON 解析尝试失败: {e}")
            return None

    def _build_graph_from_data(self, data: dict) -> Optional[PlanGraph]:
        """从解析后的 JSON 数据构建 PlanGraph

        支持的 JSON 结构:
        {
            "tasks": [ { "id": ..., "description": ..., ... }, ... ],
            "root_task_id": "task_1"
        }

        Args:
            data: 解析后的字典

        Returns:
            PlanGraph 或 None（数据无效）
        """
        if not isinstance(data, dict):
            return None

        tasks_data = data.get("tasks", [])
        if not tasks_data or not isinstance(tasks_data, list):
            return None

        nodes: Dict[str, PlanNode] = {}
        for item in tasks_data:
            if not isinstance(item, dict):
                continue

            node_id = item.get("id", "")
            if not node_id:
                continue

            # 解析 assigned_role
            role = None
            role_str = item.get("assigned_role")
            if role_str:
                try:
                    role = AgentRole(role_str)
                except ValueError:
                    logger.debug(f"未知的 Agent 角色: {role_str}")

            node = PlanNode(
                id=node_id,
                description=item.get("description", ""),
                dependencies=item.get("dependencies", []),
                estimated_duration=item.get("estimated_duration"),
                assigned_role=role,
                status=TaskStatus.PENDING,
            )
            nodes[node_id] = node

        if not nodes:
            return None

        root_node_id = data.get(
            "root_task_id",
            list(nodes.keys())[0] if nodes else "",
        )

        return PlanGraph(nodes=nodes, root_node_id=root_node_id)

    def _fallback_single_task(self, task_description: str) -> PlanGraph:
        """回退策略：将整个任务作为单个节点

        当 LLM 响应无法被解析为结构化 JSON 时使用。

        Args:
            task_description: 原始任务描述

        Returns:
            包含单个根节点的 PlanGraph
        """
        node_id = str(uuid.uuid4())
        node = PlanNode(
            id=node_id,
            description=task_description.strip(),
            dependencies=[],
            estimated_duration=None,
            assigned_role=None,
            status=TaskStatus.PENDING,
        )
        return PlanGraph(nodes={node_id: node}, root_node_id=node_id)

    def _validate_dag(self, graph: PlanGraph) -> None:
        """验证规划图为有效 DAG

        - 检查 root_node_id 是否存在
        - 检测循环依赖
        - 验证依赖引用有效性

        Args:
            graph: 待验证的 PlanGraph

        Raises:
            ValidationException: 图中存在循环依赖或无效引用时抛出
        """
        if not graph.nodes:
            raise ValidationException("规划图为空，没有子任务节点")

        if graph.root_node_id and graph.root_node_id not in graph.nodes:
            raise ValidationException(
                f"根节点 '{graph.root_node_id}' 不在节点列表中"
            )

        # 验证所有依赖引用指向存在的节点
        for nid, node in graph.nodes.items():
            for dep in node.dependencies:
                if dep not in graph.nodes:
                    logger.warning(
                        f"节点 '{nid}' 依赖了不存在的节点 '{dep}'"
                    )

        # 检测循环依赖
        if not graph.validate_no_cycles():
            raise ValidationException(
                "任务规划图中存在循环依赖，无法执行"
            )

        logger.info("DAG 验证通过")

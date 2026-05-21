"""
AgentForge ResearcherAgent - 研究分析专家

负责信息检索、资料收集和研究分析工作。
可调用 web_search 等工具获取外部信息。
"""
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_forge.agents.base import BaseAgent
from agent_forge.core.cancellation import CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.models.schemas import AgentRole, AgentStep, StepType
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class ResearcherAgent(BaseAgent):
    """研究分析 Agent

    专注于信息检索、资料收集和研究分析。
    通过调用搜索工具获取信息，并使用 LLM 进行分析综合。
    """

    role: AgentRole = AgentRole.RESEARCHER
    name: str = "Researcher"
    description: str = "研究分析专家，擅长信息检索和资料收集"

    def __init__(
        self,
        llm_router: LLMRouter,
        tool_registry: Optional[Any] = None,
    ):
        """初始化 ResearcherAgent

        Args:
            llm_router: LLM 路由器实例
            tool_registry: 可选的工具注册中心
        """
        super().__init__(llm_router, tool_registry)
        self.search_tools: Dict[str, Any] = {}

        if tool_registry:
            try:
                tool_list = tool_registry.list_tools(category="search", include_schema=False)
                for t in tool_list:
                    self.search_tools[t["name"]] = t
            except Exception:
                pass
            # 如果没有搜索分类的工具，尝试获取所有工具
            if not self.search_tools:
                try:
                    tool_list = tool_registry.list_tools(include_schema=False)
                    for t in tool_list:
                        self.search_tools[t["name"]] = t
                except Exception:
                    pass

    def get_system_prompt(self) -> str:
        """获取研究员系统提示词"""
        base_prompt = (
            "你是一个专业的研究员，擅长信息检索和资料收集。\n"
            "你的职责包括：\n"
            "1. 使用 WebSearch 工具搜索外部信息\n"
            "2. 分析和综合收集到的信息\n"
            "3. 形成有深度、有见解的研究报告\n"
            "4. 验证信息的准确性和可靠性\n"
            "请根据需求完成研究任务。"
        )

        if self.search_tools:
            tools_desc = "\n".join(
                f"- {name}: {info.get('description', '无描述')}"
                for name, info in self.search_tools.items()
            )
            base_prompt += f"\n\n可用搜索工具:\n{tools_desc}"

        return base_prompt

    async def _try_search(self, task: Any) -> Optional[str]:
        """尝试使用搜索工具获取信息

        Args:
            task: 任务对象

        Returns:
            搜索结果字符串，无工具时返回 None
        """
        if not self.tool_registry or not self.search_tools:
            return None

        try:
            task_description = task.description if hasattr(task, "description") else str(task)
            # 尝试使用第一个搜索工具
            tool_name = list(self.search_tools.keys())[0]
            tool = self.tool_registry.get(tool_name)
            if tool:
                result = await tool.execute(query=task_description)
                return f"搜索结果:\n{result}"
        except Exception as e:
            logger.warning(f"搜索失败: {e}")

        return None

    async def execute(  # type: ignore[override]
        self,
        task: Any,
        context: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行研究任务

        Args:
            task: 研究任务对象或描述
            context: 可选的上下文信息
            cancellation_token: 可选的取消令牌

        Yields:
            AgentStep: 研究过程中的各个步骤
        """
        await self.on_task_start(task)

        try:
            task_description = task.description if hasattr(task, "description") else str(task)
            task_id = task.id if hasattr(task, "id") else "unknown"

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self.get_system_prompt()},
            ]
            if context:
                messages.append({"role": "user", "content": f"背景信息:\n{context}"})
            messages.append({"role": "user", "content": f"研究任务:\n{task_description}"})

            if cancellation_token:
                await cancellation_token.check_cancellation()

            # 第一步：思考研究策略
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=1,
                step_type=StepType.THOUGHT,
                content=f"分析研究任务: {task_description[:100]}",
            )

            # 尝试搜索
            search_result = await self._try_search(task)

            if search_result:
                # 第二步：行动（搜索）
                yield AgentStep(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    step_number=2,
                    step_type=StepType.ACTION,
                    content="执行搜索获取信息",
                )

                # 第三步：观察（搜索结果）
                yield AgentStep(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    step_number=3,
                    step_type=StepType.OBSERVATION,
                    content=search_result,
                )

                messages.append({"role": "user", "content": search_result})

            # 调用 LLM 生成研究结论
            response = await self.llm_router.route(
                messages=messages,
                complexity="complex",
            )

            # 第四步：最终结果
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=4,
                step_type=StepType.FINAL,
                content=response.content,
            )

        except Exception as e:
            logger.error(f"ResearcherAgent 执行出错: {e}")
            task_id = task.id if hasattr(task, "id") else "unknown"
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=0,
                step_type=StepType.ERROR,
                content=str(e),
            )

    def _parse_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """从 LLM 输出中解析工具调用

        Args:
            content: LLM 输出内容

        Returns:
            工具调用字典或 None
        """
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_str)
                if isinstance(data, dict) and "tool_name" in data:
                    return data
        except (json.JSONDecodeError, IndexError):
            pass
        return None

    async def _execute_search(self, tool_name: str, params: Dict[str, Any]) -> str:
        """执行搜索工具

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            搜索结果字符串
        """
        if self.tool_registry:
            try:
                tool = self.tool_registry.get(tool_name)
                if tool:
                    result = await tool.execute(**params)
                    return str(result)
            except Exception as e:
                return f"搜索失败: {e}"

        return f"搜索工具 '{tool_name}' 不可用"

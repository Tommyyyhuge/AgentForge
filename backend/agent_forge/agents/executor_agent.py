"""
AgentForge ExecutorAgent - 通用任务执行者

负责执行具体任务，可调用各种工具完成工作。
ExecutorAgent 是默认的 Agent 角色，适用于通用场景。
"""
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_forge.agents.base import BaseAgent
from agent_forge.core.cancellation import CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.models.schemas import AgentRole, AgentStep, StepType
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class ExecutorAgent(BaseAgent):
    """通用执行 Agent

    能够执行各种类型的任务，集成 LLM 推理和工具调用能力。
    通过 thought -> action -> observation -> final 的四步流程完成任务。
    """

    role: AgentRole = AgentRole.EXECUTOR
    name: str = "Executor"
    description: str = "通用任务执行 Agent，可调用工具完成各种任务"

    def __init__(
        self,
        llm_router: LLMRouter,
        tool_registry: Optional[Any] = None,
    ):
        """初始化 ExecutorAgent

        Args:
            llm_router: LLM 路由器实例
            tool_registry: 可选的工具注册中心
        """
        super().__init__(llm_router, tool_registry)
        self.tools: Dict[str, Any] = {}
        if tool_registry:
            try:
                tool_list = tool_registry.list_tools(include_schema=False)
                for t in tool_list:
                    self.tools[t["name"]] = t
            except Exception:
                pass

    def get_system_prompt(self) -> str:
        """获取任务执行者系统提示词"""
        base_prompt = (
            "你是一个高效的任务执行者 Agent。\n"
            "你的职责是受理分配给你的任务，分析需求，利用可用工具高效完成任务并汇报结果。\n"
            "工作原则：\n"
            "1. 仔细理解任务需求，明确目标和约束\n"
            "2. 制定合理的执行计划，分解为可操作的步骤\n"
            "3. 使用可用工具高效完成任务\n"
            "4. 遇到问题时分析原因并尝试替代方案\n"
            "5. 完成后提供清晰的结果总结"
        )
        tools_desc = self._get_tools_description()
        if tools_desc:
            base_prompt += f"\n\n可用工具:\n{tools_desc}"
        return base_prompt

    def _get_tools_description(self) -> str:
        """获取工具描述"""
        if not self.tools:
            return ""
        desc_lines = []
        for name, tool_info in self.tools.items():
            desc = tool_info.get("description", "无描述")
            desc_lines.append(f"- {name}: {desc}")
        return "\n".join(desc_lines)

    async def execute(
        self,
        task: Any,
        context: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行任务

        按照 thought -> action -> observation -> final 流程执行。

        Args:
            task: 任务对象或任务描述字符串
            context: 可选的上下文信息
            cancellation_token: 可选的取消令牌

        Yields:
            AgentStep: 思考、行动、观察或最终结果步骤
        """
        await self.on_task_start(task)

        try:
            task_description = task.description if hasattr(task, "description") else str(task)
            task_id = task.id if hasattr(task, "id") else "unknown"

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self.get_system_prompt()},
            ]
            if context:
                messages.append({"role": "user", "content": f"上下文信息:\n{context}"})
            messages.append({"role": "user", "content": f"任务:\n{task_description}"})

            # 添加记忆上下文
            if self.memory:
                memory_str = self.get_memory_context()
                messages.append({"role": "system", "content": f"历史记忆:\n{memory_str}"})

            if cancellation_token:
                await cancellation_token.check_cancellation()

            # 第一步：思考
            response = await self.llm_router.route(
                messages=messages,
                complexity="medium",
            )

            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=1,
                step_type=StepType.THOUGHT,
                content=response.content,
            )

            # 尝试解析行动
            parsed_action = self._parse_action(response.content)

            if parsed_action and "tool_name" in parsed_action:
                # 第二步：行动（工具调用）
                tool_name = parsed_action["tool_name"]
                tool_params = parsed_action.get("parameters", {})

                yield AgentStep(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    step_number=2,
                    step_type=StepType.ACTION,
                    content=f"调用工具: {tool_name}",
                    tool_name=tool_name,
                    tool_input=tool_params,
                )

                # 第三步：观察（工具执行结果）
                observation = await self._execute_tool(tool_name, tool_params)

                yield AgentStep(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    step_number=3,
                    step_type=StepType.OBSERVATION,
                    content=observation,
                )

                # 再次调用 LLM 获取最终结果
                messages.append({"role": "user", "content": f"工具返回:\n{observation}"})
                final_response = await self.llm_router.route(
                    messages=messages,
                    complexity="medium",
                )
            else:
                # 没有工具调用，模拟 ACTION 和 OBSERVATION
                yield AgentStep(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    step_number=2,
                    step_type=StepType.ACTION,
                    content="分析任务需求",
                )

                yield AgentStep(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    step_number=3,
                    step_type=StepType.OBSERVATION,
                    content="任务分析完成",
                )

                final_response = response

            # 第四步：最终结果
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=4,
                step_type=StepType.FINAL,
                content=final_response.content,
            )

        except Exception as e:
            logger.error(f"ExecutorAgent 执行出错: {e}")
            task_id = task.id if hasattr(task, "id") else "unknown"
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=0,
                step_type=StepType.ERROR,
                content=str(e),
            )

    def _parse_action(self, thought: str) -> Optional[Dict[str, Any]]:
        """从思考内容中解析行动指令

        尝试从 JSON 代码块中提取工具调用信息。

        Args:
            thought: LLM 生成的思考内容

        Returns:
            解析后的行动字典，如果无法解析则返回 None
        """
        try:
            # 查找 JSON 块
            if "```json" in thought:
                json_str = thought.split("```json")[1].split("```")[0].strip()
            elif "```" in thought:
                json_str = thought.split("```")[1].split("```")[0].strip()
            else:
                # 尝试直接解析
                json_str = thought.strip()

            data = json.loads(json_str)
            if isinstance(data, dict) and "tool_name" in data:
                return data
        except (json.JSONDecodeError, IndexError):
            pass
        return None

    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """执行工具调用

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            工具执行结果字符串
        """
        if self.tool_registry:
            try:
                tool = self.tool_registry.get(tool_name)
                if tool:
                    result = await tool.execute(**parameters)
                    return str(result)
            except Exception as e:
                return f"工具执行失败: {e}"

        return f"工具 '{tool_name}' 不可用（未注册 tool_registry）"

"""
AgentForge ReAct 循环引擎模块

实现 ReAct (Reasoning + Acting) 循环引擎。
支持思考-行动-观察的迭代过程，直到获得最终答案。
"""
import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import BaseModel, Field

from agent_forge.core.cancellation import CancellationError, CancellationToken
from agent_forge.core.error_handler import LLMException
from agent_forge.core.llm_client import LLMResponse, LLMRouter
from agent_forge.core.output_validator import OutputValidator, ValidationError
from agent_forge.models.schemas import AgentRole, AgentStep, StepType
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class ReActOutput(BaseModel):
    """ReAct 输出结构

    定义 LLM 在每一步应返回的结构化输出格式。
    """

    thought: str = Field(description="对当前情况的思考和分析")
    action: Optional[Dict[str, Any]] = Field(
        default=None, description="要执行的动作，包含 tool_name 和 parameters"
    )
    is_final: bool = Field(default=False, description="是否已得到最终答案")
    final_answer: Optional[str] = Field(
        default=None, description="最终答案（当 is_final=true 时）"
    )


class ReActLoop:
    """ReAct 循环引擎

    执行思考-行动-观察的迭代循环，直到获得最终答案或达到最大步数。
    支持工具调用、取消令牌和结构化输出验证。

    使用方式:
        loop = ReActLoop(llm_router, tools)
        async for step in loop.run(task="计算 1+1", task_id="task_001"):
            print(step)
    """

    # ReAct 提示模板
    REACT_PROMPT_TEMPLATE = """你是一个智能助手，使用 ReAct (Reasoning + Acting) 方式解决问题。

当前任务: {task}

上下文信息:
{context}

可用工具:
{tools_description}

历史步骤:
{history}

请按照以下 JSON 格式输出你的思考结果:
{{
    "thought": "你的思考过程",
    "action": {{
        "tool_name": "工具名称（如果需要行动）",
        "parameters": {{参数}}
    }},
    "is_final": false,
    "final_answer": null
}}

如果你已经得到最终答案，设置 is_final 为 true 并提供 final_answer。"""

    def __init__(
        self,
        llm_router: LLMRouter,
        tools: List[Any],
        max_steps: int = 10,
    ):
        """初始化 ReAct 循环引擎

        Args:
            llm_router: LLM 路由器实例
            tools: 可用工具列表，每个工具需要有 name 和 execute 属性
            max_steps: 最大执行步数，防止无限循环
        """
        self.llm_router = llm_router
        self.tools: Dict[str, Any] = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.validator = OutputValidator(ReActOutput)

    async def run(
        self,
        task: str,
        task_id: str,
        context: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行 ReAct 循环

        迭代执行思考-行动-观察流程，每次迭代：
        1. 构建提示词并调用 LLM
        2. 解析 LLM 输出为结构化数据
        3. 如果包含行动，执行工具并返回观察结果
        4. 如果标记为最终，返回最终答案

        Args:
            task: 任务描述字符串
            task_id: 任务 ID，用于追踪
            context: 可选的上下文信息
            cancellation_token: 可选的取消令牌

        Yields:
            AgentStep: 每个执行步骤

        Raises:
            CancellationError: 任务被取消时抛出
        """
        agent_id = f"react_loop_{task_id[:8]}"
        steps_history: List[str] = []
        tools_description = self._build_tools_description()

        for step in range(1, self.max_steps + 1):
            # 检查取消
            if cancellation_token:
                await cancellation_token.check_cancellation()

            # 构建提示词
            prompt = self.REACT_PROMPT_TEMPLATE.format(
                task=task,
                context=context or "无",
                tools_description=tools_description,
                history="\n".join(steps_history[-5:]) if steps_history else "无",
            )

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"请完成第 {step} 步的思考和行动。"},
            ]

            # 调用 LLM
            try:
                response: LLMResponse = await self.llm_router.route(
                    messages=messages,
                    complexity="medium",
                )
            except LLMException as e:
                yield AgentStep(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_role=AgentRole.EXECUTOR,
                    step_number=step,
                    step_type=StepType.ERROR,
                    content=f"LLM 调用失败: {e}",
                )
                return

            content = response.content

            # 解析 LLM 输出
            parsed = self._parse_react_output(content)

            if parsed is None:
                yield AgentStep(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_role=AgentRole.EXECUTOR,
                    step_number=step,
                    step_type=StepType.ERROR,
                    content=f"无法解析 LLM 输出: {content[:200]}",
                )
                return

            # 输出思考步骤
            yield AgentStep(
                task_id=task_id,
                agent_id=agent_id,
                agent_role=AgentRole.EXECUTOR,
                step_number=step,
                step_type=StepType.THOUGHT,
                content=parsed.thought,
            )

            # 检查是否最终答案
            if parsed.is_final:
                yield AgentStep(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_role=AgentRole.EXECUTOR,
                    step_number=step,
                    step_type=StepType.FINAL,
                    content=parsed.final_answer or parsed.thought,
                )
                return

            # 执行行动
            if parsed.action and "tool_name" in parsed.action:
                tool_name = parsed.action["tool_name"]
                tool_params = parsed.action.get("parameters", {})

                yield AgentStep(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_role=AgentRole.EXECUTOR,
                    step_number=step,
                    step_type=StepType.ACTION,
                    content=f"调用工具: {tool_name}",
                    tool_name=tool_name,
                    tool_input=tool_params,
                )

                # 执行工具
                observation = await self._execute_tool(tool_name, tool_params)

                yield AgentStep(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_role=AgentRole.EXECUTOR,
                    step_number=step,
                    step_type=StepType.OBSERVATION,
                    content=observation,
                )

                steps_history.append(
                    f"第{step}步: 思考: {parsed.thought[:100]}... | "
                    f"行动: {tool_name} | 观察: {observation[:100]}..."
                )
            else:
                # 没有行动也没有最终标记，记录并继续
                steps_history.append(f"第{step}步: 思考: {parsed.thought[:100]}... | 无行动")
                continue

        # 达到最大步数
        yield AgentStep(
            task_id=task_id,
            agent_id=agent_id,
            agent_role=AgentRole.EXECUTOR,
            step_number=self.max_steps,
            step_type=StepType.FINAL,
            content=f"已达到最大步数 ({self.max_steps})，任务未完成",
        )

    def _build_tools_description(self) -> str:
        """构建工具描述文本

        Returns:
            格式化的工具列表描述
        """
        if not self.tools:
            return "没有可用工具"

        lines = []
        for name, tool in self.tools.items():
            desc = getattr(tool, "description", "无描述")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def _parse_react_output(self, content: str) -> Optional[ReActOutput]:
        """解析 LLM 输出为 ReActOutput

        支持从 JSON 代码块或纯 JSON 文本中解析。

        Args:
            content: LLM 输出的文本内容

        Returns:
            ReActOutput 实例，解析失败则返回 None
        """
        # 尝试提取 JSON
        json_str = None
        for delimiter in ["```json", "```"]:
            if delimiter in content:
                parts = content.split(delimiter)
                if len(parts) >= 2:
                    candidate = parts[1]
                    if "```" in candidate:
                        candidate = candidate.split("```")[0]
                    json_str = candidate.strip()
                    break

        if json_str is None:
            # 尝试整体解析
            json_str = content.strip()

        try:
            data = json.loads(json_str)
            return self.validator.validate(data)  # type: ignore
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"ReAct 输出解析失败: {e}")
            return None

    def _parse_response(self, content: str) -> ReActOutput:
        """解析 LLM 响应（兼容旧测试接口）

        Args:
            content: LLM 输出的文本内容

        Returns:
            ReActOutput 实例，解析失败时返回默认最终输出
        """
        result = self._parse_react_output(content)
        if result is not None:
            return result
        # 解析失败，返回默认最终输出
        return ReActOutput(
            thought="解析失败",
            is_final=True,
            final_answer=content,
        )

    async def _get_llm_response_with_retry(
        self,
        messages: List[Dict[str, str]],
        max_retries: int = 3,
    ) -> LLMResponse:
        """带重试的 LLM 调用（兼容旧测试接口）

        Args:
            messages: 消息列表
            max_retries: 最大重试次数

        Returns:
            LLMResponse 实例

        Raises:
            LLMException: 所有重试都失败时抛出
            CancellationError: 取消时不重试直接抛出
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return await self.llm_router.route(
                    messages=messages,
                    complexity="medium",
                )
            except CancellationError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        raise LLMException(f"LLM 调用失败，已重试 {max_retries} 次: {last_error}")

    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """执行工具调用

        Args:
            tool_name: 工具名称
            parameters: 工具参数字典

        Returns:
            工具执行结果字符串
        """
        tool = self.tools.get(tool_name)
        if tool is None:
            return f"错误: 工具 '{tool_name}' 不存在"

        try:
            result = await tool.execute(**parameters)
            return str(result)
        except Exception as e:
            return f"工具执行出错: {type(e).__name__}: {e}"

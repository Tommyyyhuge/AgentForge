"""
AgentForge CoderAgent - 代码开发专家

负责代码生成、调试和代码审查。
专注于编写高质量、可维护的代码。
"""
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_forge.agents.base import BaseAgent
from agent_forge.core.cancellation import CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.models.schemas import AgentRole, AgentStep, StepType
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class CoderAgent(BaseAgent):
    """代码开发 Agent

    专注于代码生成、调试和编程任务。
    支持多种编程语言和框架。
    """

    role: AgentRole = AgentRole.CODER
    name: str = "Coder"
    description: str = "代码开发专家，擅长编写和调试代码"

    def __init__(
        self,
        llm_router: LLMRouter,
        tool_registry: Optional[Any] = None,
    ):
        """初始化 CoderAgent

        Args:
            llm_router: LLM 路由器实例
            tool_registry: 可选的工具注册中心
        """
        super().__init__(llm_router, tool_registry)

    def get_system_prompt(self) -> str:
        """获取程序员系统提示词"""
        return (
            "你是一名资深的程序员，擅长代码生成、调试和优化。\n"
            "你的职责包括：\n"
            "1. 编写高质量、可维护的代码\n"
            "2. 代码审查和优化建议\n"
            "3. 调试和错误修复\n"
            "4. 使用 code_execute 工具测试代码\n"
            "5. 使用 file_read/file_write 工具读写文件\n"
            "请根据需求完成编程任务。"
        )

    def _build_system_prompt(self) -> str:
        """构建编程专用系统提示词"""
        base_prompt = self.get_system_prompt()
        base_prompt += (
            "\n\n你是专业软件开发工程师。你的核心能力：\n"
            "1. 代码生成：根据需求编写清晰、高效的代码\n"
            "2. 代码调试：分析和定位代码中的错误\n"
            "3. 代码优化：改进现有代码的性能和可读性\n"
            "4. 架构设计：设计合理的代码结构和模块划分\n\n"
            "编程规范：\n"
            "- 遵循语言的最佳实践和编码规范\n"
            "- 包含适当的注释和类型注解\n"
            "- 考虑边界情况和错误处理\n"
            "- 编写可测试的代码\n\n"
            "当需要执行代码或操作文件时，使用 ```json 标记指定工具调用。"
        )
        return base_prompt

    async def execute(
        self,
        task: Any,
        context: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行编程任务

        Args:
            task: 编程任务对象或描述
            context: 可选的上下文信息（如现有代码）
            cancellation_token: 可选的取消令牌

        Yields:
            AgentStep: 编程过程中的各个步骤
        """
        await self.on_task_start(task)

        try:
            task_description = task.description if hasattr(task, "description") else str(task)
            task_id = task.id if hasattr(task, "id") else "unknown"

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self._build_system_prompt()},
            ]

            # 如果有上下文（现有代码），添加到消息中
            if context:
                messages.append({
                    "role": "user",
                    "content": f"现有代码/上下文:\n```\n{context}\n```",
                })

            messages.append({"role": "user", "content": f"编程任务:\n{task_description}"})

            if cancellation_token:
                await cancellation_token.check_cancellation()

            # 第一步：思考
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=1,
                step_type=StepType.THOUGHT,
                content=f"分析编程任务: {task_description[:100]}",
            )

            # 调用 LLM
            response = await self.llm_router.route(
                messages=messages,
                complexity="complex",
            )

            # 第二步：行动
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=2,
                step_type=StepType.ACTION,
                content="调用 LLM 生成代码",
            )

            # 第三步：观察
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=3,
                step_type=StepType.OBSERVATION,
                content="代码生成完成",
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
            content: LLM 输出的内容

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

"""
AgentForge WriterAgent - 内容创作专家

负责文档撰写、内容创作和文字处理。
专注于生成高质量的中英文文档和内容。
"""
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_forge.agents.base import BaseAgent
from agent_forge.core.cancellation import CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.models.schemas import AgentRole, AgentStep, StepType
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class WriterAgent(BaseAgent):
    """内容创作 Agent

    专注于文档撰写、技术文档、报告和各类文字内容的创作。
    支持结构化文档和多种写作风格。
    """

    role: AgentRole = AgentRole.WRITER
    name: str = "Writer"
    description: str = "内容创作专家，擅长文档撰写和文字处理"

    def __init__(self, llm_router: LLMRouter, tool_registry: Optional[Any] = None):
        """初始化 WriterAgent

        Args:
            llm_router: LLM 路由器实例
            tool_registry: 工具注册中心（可选）
        """
        super().__init__(llm_router, tool_registry)

    def get_system_prompt(self) -> str:
        """获取作家系统提示词"""
        return (
            "你是一名专业的作家，擅长文档撰写和内容创作。\n"
            "你的职责包括：\n"
            "1. 撰写技术文档、报告和指南\n"
            "2. 内容创作和润色\n"
            "3. 使用 summarize 工具处理长文本\n"
            "4. 使用 file_write 工具保存文档\n"
            "请根据需求完成写作任务。"
        )

    async def execute(
        self,
        task: Any,
        context: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行写作任务

        Args:
            task: 写作任务对象或描述
            context: 可选的上下文信息或素材
            cancellation_token: 可选的取消令牌

        Yields:
            AgentStep: 写作过程中的各个步骤
        """
        await self.on_task_start(task)

        try:
            task_description = task.description if hasattr(task, "description") else str(task)
            task_id = task.id if hasattr(task, "id") else "unknown"

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self.get_system_prompt()},
            ]

            # 添加素材上下文
            if context:
                messages.append({
                    "role": "user",
                    "content": f"参考资料/素材:\n{context}",
                })

            # 添加任务需求
            messages.append({"role": "user", "content": f"写作任务:\n{task_description}"})

            if cancellation_token:
                await cancellation_token.check_cancellation()

            # 第一步：思考和规划
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=1,
                step_type=StepType.THOUGHT,
                content=f"开始分析写作任务: {task_description[:100]}",
            )

            # 调用 LLM 进行写作
            response = await self.llm_router.route(messages=messages, complexity="medium")

            # 产出行动步骤
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=2,
                step_type=StepType.ACTION,
                content="调用 LLM 完成写作",
            )

            # 产出观察步骤
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=3,
                step_type=StepType.OBSERVATION,
                content="写作完成",
            )

            # 产出最终结果
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=4,
                step_type=StepType.FINAL,
                content=response.content,
            )

        except Exception as e:
            logger.error(f"WriterAgent 执行出错: {e}")
            yield AgentStep(
                task_id=task_id if "task_id" in locals() else "unknown",
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=1,
                step_type=StepType.ERROR,
                content=f"写作任务失败: {e}",
            )

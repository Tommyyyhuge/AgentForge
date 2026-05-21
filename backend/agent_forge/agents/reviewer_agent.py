"""
AgentForge ReviewerAgent - 代码审查专家

负责代码审查、质量检查和最佳实践验证。
确保代码质量和项目规范的一致性。
"""
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_forge.agents.base import BaseAgent
from agent_forge.core.cancellation import CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.models.schemas import AgentRole, AgentStep, StepType
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class ReviewerAgent(BaseAgent):
    """代码审查 Agent

    专注于代码质量审查、最佳实践验证和问题发现。
    提供结构化的审查报告和改进建议。
    """

    role: AgentRole = AgentRole.REVIEWER
    name: str = "Reviewer"
    description: str = "代码审查专家，擅长质量检查和最佳实践验证"

    def __init__(self, llm_router: LLMRouter, tool_registry: Optional[Any] = None):
        """初始化 ReviewerAgent

        Args:
            llm_router: LLM 路由器实例
            tool_registry: 工具注册中心（可选）
        """
        super().__init__(llm_router, tool_registry)

    def get_system_prompt(self) -> str:
        """获取审查员系统提示词"""
        return (
            "你是一名严格的质量审查员，擅长代码审查和质量检查。\n"
            "你的职责包括：\n"
            "1. 代码审查（风格、安全、性能）\n"
            "2. 文档质量检查\n"
            "3. 逻辑一致性验证\n"
            "4. 使用 file_read 工具读取待审查内容\n"
            "5. 提供详细的审查报告和改进建议\n"
            "请严格审查，找出所有问题。"
        )

    async def execute(  # type: ignore[override]
        self,
        task: Any,
        context: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentStep, None]:
        """执行审查任务

        Args:
            task: 审查任务对象或描述
            context: 待审查的代码或文档内容
            cancellation_token: 可选的取消令牌

        Yields:
            AgentStep: 审查过程中的各个步骤
        """
        await self.on_task_start(task)

        try:
            task_description = task.description if hasattr(task, "description") else str(task)
            task_id = task.id if hasattr(task, "id") else "unknown"

            # 构建审查消息
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self.get_system_prompt()},
            ]

            if context:
                messages.append({
                    "role": "user",
                    "content": f"待审查内容:\n```\n{context}\n```",
                })

            messages.append({
                "role": "user",
                "content": f"审查要求:\n{task_description}",
            })

            if cancellation_token:
                await cancellation_token.check_cancellation()

            # 第一步：思考审查策略
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=1,
                step_type=StepType.THOUGHT,
                content=f"开始审查任务: {task_description[:100]}",
            )

            # 调用 LLM 进行审查
            response = await self.llm_router.route(messages=messages, complexity="medium")

            # 产出行动步骤
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=2,
                step_type=StepType.ACTION,
                content="调用 LLM 完成审查分析",
            )

            # 产出观察步骤
            yield AgentStep(
                task_id=task_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=3,
                step_type=StepType.OBSERVATION,
                content="审查分析完成",
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
            logger.error(f"ReviewerAgent 执行出错: {e}")
            yield AgentStep(
                task_id=task_id if "task_id" in locals() else "unknown",
                agent_id=self.agent_id,
                agent_role=self.role,
                step_number=1,
                step_type=StepType.ERROR,
                content=f"审查任务失败: {e}",
            )

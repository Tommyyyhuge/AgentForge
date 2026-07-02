"""
AgentForge Agent 消息工具模块

封装 A2A 消息总线，让 Agent 通过工具调用方式发送消息。
支持点对点发送和带超时的请求-响应模式。
"""
import logging
from typing import Optional

from agent_forge.core.a2a_bus import A2ABus, A2AMessage
from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# 默认 A2A 总线实例（模块级单例，便于工具共享同一总线）
_default_bus: Optional[A2ABus] = None


def _get_default_bus() -> A2ABus:
    """获取默认 A2A 总线实例

    Returns:
        A2ABus 单例实例
    """
    global _default_bus
    if _default_bus is None:
        _default_bus = A2ABus()
    return _default_bus


class AgentMessageTool(BaseTool):
    """Agent 消息工具

    封装 A2A 消息总线，允许 Agent 通过工具调用与其他 Agent 通信。
    支持：
    - 点对点发送消息
    - 请求-响应模式（带超时等待）
    """

    name: str = "agent_message"
    description: str = "向其他 Agent 发送消息，支持点对点和请求-响应模式"
    version: str = "1.0"

    def __init__(self, a2a_bus: Optional[A2ABus] = None):
        """初始化消息工具

        Args:
            a2a_bus: A2A 总线实例，未提供时使用默认实例
        """
        self.a2a_bus: A2ABus = a2a_bus or _get_default_bus()
        super().__init__()

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义消息工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "receiver_role": {
                    "type": "string",
                    "description": "接收消息的可执行 Agent 角色名（如 researcher, coder, reviewer）",
                },
                "message": {
                    "type": "string",
                    "description": "要发送的消息内容",
                },
                "wait_response": {
                    "type": "boolean",
                    "description": "是否等待对方的响应，默认 false",
                    "default": False,
                },
                "timeout": {
                    "type": "number",
                    "description": "等待响应的超时秒数，仅 wait_response=true 时有效，默认 30",
                    "default": 30.0,
                },
            },
            required=["receiver_role", "message"],
            examples=[
                {
                    "receiver_role": "researcher",
                    "message": "请搜索最新的 Python 异步编程资料",
                },
                {
                    "receiver_role": "reviewer",
                    "message": "当前任务已完成，请审查输出质量。",
                    "wait_response": True,
                    "timeout": 15.0,
                },
            ],
        )

    async def execute(self, **kwargs) -> str:
        """执行消息发送

        Args:
            **kwargs: 工具参数，包含:
                - receiver_role: 接收消息的 Agent 角色名
                - message: 消息内容
                - wait_response: 是否等待响应（默认 False）
                - timeout: 等待超时秒数（默认 30）

        Returns:
            发送结果字符串，若 wait_response=True 则包含响应内容
        """
        receiver_role: str = kwargs.get("receiver_role", "")
        message: str = kwargs.get("message", "")
        wait_response: bool = kwargs.get("wait_response", False)
        timeout: float = kwargs.get("timeout", 30.0)

        logger.info(
            "agent_message 发送消息: %s -> %s (wait=%s)",
            "current_agent",
            receiver_role,
            wait_response,
        )

        if not receiver_role or not receiver_role.strip():
            return "[消息错误] 接收者角色不能为空"

        if not message or not message.strip():
            return "[消息错误] 消息内容不能为空"

        if receiver_role.strip().lower() == "planner":
            return (
                "[消息错误] Planner is a planning component, not an executable "
                "Agent receiver. Use researcher, coder, writer, reviewer, or executor."
            )

        # 创建 A2A 消息
        a2a_msg: A2AMessage = A2AMessage(
            sender_id="agent_message_tool",
            content=message.strip(),
            receiver_id=receiver_role.strip(),
            message_type="request" if wait_response else "broadcast",
        )

        try:
            if wait_response:
                # 请求-响应模式
                timeout = max(1.0, min(timeout, 120.0))

                response: Optional[A2AMessage] = await self.a2a_bus.request_response(
                    request=a2a_msg,
                    timeout=timeout,
                )

                if response is None:
                    logger.warning(
                        "agent_message 等待响应超时: %s (%.1fs)",
                        receiver_role,
                        timeout,
                    )
                    return (
                        f"消息已发送至 {receiver_role}，但在 {timeout} 秒内未收到响应。\n"
                        f"发送内容: {message[:200]}"
                    )

                response_content: str = response.content
                logger.info(
                    "agent_message 收到响应: %s <- %s",
                    receiver_role,
                    "sender",
                )
                return (
                    f"消息已发送至 {receiver_role}，收到响应:\n"
                    f"---\n"
                    f"{response_content}"
                )

            else:
                # 点对点发送
                await self.a2a_bus.send(a2a_msg)
                logger.info(
                    "agent_message 消息已发送: -> %s", receiver_role
                )
                return (
                    f"消息已成功发送至 {receiver_role}。\n"
                    f"发送内容: {message[:200]}"
                )

        except Exception as e:
            logger.error("agent_message 发送失败: %s", e)
            return f"[消息错误] 消息发送失败: {e}"


__all__ = ["AgentMessageTool"]

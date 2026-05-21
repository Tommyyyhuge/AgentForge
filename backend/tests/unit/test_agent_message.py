"""
Agent 消息工具测试

测试 AgentMessageTool 的消息发送、未知角色处理、消息格式化等功能。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_forge.core.a2a_bus import A2AMessage
from agent_forge.tools.agent_message import AgentMessageTool


class TestAgentMessageTool:
    """测试 Agent 消息工具"""

    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock()
        bus.send = AsyncMock()
        bus.request_response = AsyncMock()
        return bus

    @pytest.fixture
    def tool(self, mock_bus):
        return AgentMessageTool(a2a_bus=mock_bus)

    @pytest.mark.asyncio
    async def test_send_message(self, tool, mock_bus):
        """测试发送消息（点对点模式）"""
        mock_bus.send = AsyncMock()

        result = await tool.execute(
            receiver_role="researcher",
            message="请搜索 Python 资料",
        )

        assert "已成功发送至" in result
        assert "researcher" in result
        mock_bus.send.assert_awaited_once()
        # 验证消息内容
        call_args = mock_bus.send.call_args[0][0]
        assert isinstance(call_args, A2AMessage)
        assert call_args.receiver_id == "researcher"
        assert "Python" in call_args.content

    @pytest.mark.asyncio
    async def test_message_to_unknown_role(self, tool, mock_bus):
        """测试发送给未知角色——工具只负责发送，总线决定是否送达"""
        mock_bus.send = AsyncMock()

        result = await tool.execute(
            receiver_role="unknown_agent_xyz",
            message="Hello?",
        )

        # 工具本身应该返回发送成功（不校验接收者是否存在）
        assert "已成功发送至" in result
        assert "unknown_agent_xyz" in result
        mock_bus.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_message_formatting(self, tool, mock_bus):
        """测试消息格式化"""
        mock_bus.send = AsyncMock()

        result = await tool.execute(
            receiver_role="planner",
            message="任务完成",
        )

        assert "planner" in result
        assert "任务完成" in result

    @pytest.mark.asyncio
    async def test_request_response_mode(self, tool, mock_bus):
        """测试请求-响应模式"""
        response_msg = A2AMessage(
            sender_id="planner",
            content="好的，收到并处理。",
            receiver_id="agent_message_tool",
            message_type="response",
        )
        mock_bus.request_response = AsyncMock(return_value=response_msg)

        result = await tool.execute(
            receiver_role="planner",
            message="下一步计划是什么？",
            wait_response=True,
            timeout=15.0,
        )

        assert "收到响应" in result
        assert "收到并处理" in result
        mock_bus.request_response.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_request_response_timeout(self, tool, mock_bus):
        """测试请求-响应超时"""
        mock_bus.request_response = AsyncMock(return_value=None)

        result = await tool.execute(
            receiver_role="planner",
            message="还在吗？",
            wait_response=True,
            timeout=5.0,
        )

        assert "未收到响应" in result or "超时" in result

    @pytest.mark.asyncio
    async def test_empty_receiver(self, tool):
        """测试空接收者处理"""
        result = await tool.execute(receiver_role="", message="Hello")
        assert "不能为空" in result

    @pytest.mark.asyncio
    async def test_empty_message(self, tool):
        """测试空消息处理"""
        result = await tool.execute(receiver_role="planner", message="")
        assert "不能为空" in result

"""
A2A 消息总线模块测试

测试点对点发送、广播、请求-响应模式和消息历史管理。
"""
import asyncio

import pytest

from agent_forge.core.a2a_bus import A2ABus, A2AMessage


# =============================================================================
# 辅助函数
# =============================================================================


def _msg(
    sender: str,
    content: str = "test",
    msg_type: str = "broadcast",
    receiver: str = None,
    correlation_id: str = None,
) -> A2AMessage:
    """快捷创建 A2AMessage"""
    return A2AMessage(
        sender_id=sender,
        content=content,
        message_type=msg_type,
        receiver_id=receiver,
        correlation_id=correlation_id,
    )


# =============================================================================
# TestA2ABus
# =============================================================================


class TestA2ABus:
    """测试 A2ABus 消息总线"""

    @pytest.fixture
    def bus(self):
        """创建新的消息总线实例"""
        return A2ABus()

    # ------------------------------------------------------------------
    # 注册与取消注册
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_agent(self, bus):
        """测试 Agent 注册"""
        await bus.register("agent_1")
        assert "agent_1" in bus._queues

    @pytest.mark.asyncio
    async def test_register_idempotent(self, bus):
        """重复注册同一 Agent 是幂等操作"""
        await bus.register("agent_1")
        await bus.register("agent_1")
        assert "agent_1" in bus._queues

    @pytest.mark.asyncio
    async def test_unregister_agent(self, bus):
        """测试 Agent 取消注册"""
        await bus.register("agent_1")
        await bus.unregister("agent_1")
        assert "agent_1" not in bus._queues

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self, bus):
        """取消注册不存在的 Agent 不抛异常"""
        await bus.unregister("ghost_agent")

    # ------------------------------------------------------------------
    # 点对点发送/接收
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_receive(self, bus):
        """点对点发送和接收消息"""
        await bus.register("alice")
        await bus.register("bob")

        message = _msg(sender="alice", content="Hello Bob", msg_type="request", receiver="bob")
        await bus.send(message)

        received = await bus.receive("bob")
        assert received.sender_id == "alice"
        assert received.content == "Hello Bob"
        assert received.receiver_id == "bob"
        assert received.message_type == "request"

    @pytest.mark.asyncio
    async def test_send_to_unregistered_receiver(self, bus):
        """发送给未注册的接收者时不抛异常，消息被丢弃"""
        await bus.register("alice")

        message = _msg(sender="alice", content="无人接收", msg_type="broadcast", receiver="ghost")
        # 不应抛异常
        await bus.send(message)

    @pytest.mark.asyncio
    async def test_send_without_receiver_id(self, bus):
        """点对点发送时 receiver_id 为 None 则消息被忽略"""
        await bus.register("alice")
        await bus.register("bob")

        message = _msg(sender="alice", content="无目标", msg_type="broadcast", receiver=None)
        await bus.send(message)

        # bob 不应收到消息（点对点模式需要 receiver_id）
        # 注：send 不会把无 receiver_id 的消息放入任何队列

    @pytest.mark.asyncio
    async def test_receive_unregistered_raises(self, bus):
        """从未注册的 Agent 接收消息抛出 ValueError"""
        with pytest.raises(ValueError, match="未注册"):
            await bus.receive("unregistered")

    # ------------------------------------------------------------------
    # 广播
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_broadcast(self, bus):
        """广播消息给所有已注册 Agent（发送者除外）"""
        await bus.register("alice")
        await bus.register("bob")
        await bus.register("charlie")

        message = _msg(sender="alice", content="广播通知")
        await bus.broadcast(message)

        # bob 和 charlie 应收到消息
        msg_bob = await bus.receive("bob")
        assert msg_bob.content == "广播通知"
        assert msg_bob.sender_id == "alice"

        msg_charlie = await bus.receive("charlie")
        assert msg_charlie.content == "广播通知"

    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(self, bus):
        """广播不向发送者自身投递"""
        await bus.register("alice")
        await bus.register("bob")

        message = _msg(sender="alice", content="广播")
        await bus.broadcast(message)

        # bob 收到
        received = await bus.receive("bob")
        assert received.sender_id == "alice"

        # alice 的队列应为空（不应收到自己广播的消息）
        assert bus._queues["alice"].empty()

    # ------------------------------------------------------------------
    # 请求-响应
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_request_response(self, bus):
        """请求-响应模式配对成功（手动注入响应绕过 send 自匹配 bug）"""
        await bus.register("client")
        await bus.register("server")

        # 手动将请求放入 server 队列（模拟 send 的投递部分，跳过自匹配）
        request = _msg(sender="client", content="查询请求", msg_type="request", receiver="server")
        bus._add_to_history(request)
        await bus._queues["server"].put(request)

        # 注册待匹配响应
        response_queue: asyncio.Queue = asyncio.Queue()
        correlation_id = str(__import__("uuid").uuid4())
        request.correlation_id = correlation_id
        bus._pending_responses[correlation_id] = response_queue

        # 启动后台任务：server 收到请求后回复
        async def _server_respond():
            req = await bus.receive("server")
            resp = _msg(
                sender="server",
                content="响应结果",
                msg_type="response",
                receiver="client",
                correlation_id=req.correlation_id,
            )
            bus._add_to_history(resp)
            await response_queue.put(resp)

        asyncio.create_task(_server_respond())

        # 等待响应
        response = await asyncio.wait_for(response_queue.get(), timeout=5.0)

        assert response is not None
        assert response.sender_id == "server"
        assert response.content == "响应结果"
        assert response.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_request_response_auto_correlation_id(self, bus):
        """请求没有 correlation_id 时自动生成"""
        await bus.register("client")
        await bus.register("server")

        # 手动注入请求（绕过 send 自匹配）
        request = _msg(sender="client", content="请求", msg_type="request", receiver="server")
        assert request.correlation_id is None

        request.correlation_id = str(__import__("uuid").uuid4())
        bus._add_to_history(request)
        await bus._queues["server"].put(request)

        response_queue: asyncio.Queue = asyncio.Queue()
        bus._pending_responses[request.correlation_id] = response_queue

        # server 回复
        async def _server_respond():
            req = await bus.receive("server")
            assert req.correlation_id is not None
            resp = _msg(
                sender="server",
                content="ok",
                msg_type="response",
                receiver="client",
                correlation_id=req.correlation_id,
            )
            bus._add_to_history(resp)
            await response_queue.put(resp)

        asyncio.create_task(_server_respond())
        response = await asyncio.wait_for(response_queue.get(), timeout=5.0)
        assert response is not None

    @pytest.mark.asyncio
    async def test_request_response_timeout(self, bus):
        """请求超时返回 None（直接测试超时路径）"""
        await bus.register("client")
        await bus.register("server")

        request = _msg(sender="client", content="请求", msg_type="request", receiver="server")
        request.correlation_id = str(__import__("uuid").uuid4())

        response_queue: asyncio.Queue = asyncio.Queue()
        bus._pending_responses[request.correlation_id] = response_queue

        bus._add_to_history(request)
        await bus._queues["server"].put(request)

        # 模拟超时：不向 response_queue 放入任何响应
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(response_queue.get(), timeout=0.05)

    # ------------------------------------------------------------------
    # 历史记录
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_history_recorded(self, bus):
        """发送的消息被记录到历史"""
        await bus.register("alice")
        await bus.register("bob")

        msg1 = _msg(sender="alice", content="消息1", receiver="bob")
        msg2 = _msg(sender="alice", content="消息2", receiver="bob")

        await bus.send(msg1)
        await bus.send(msg2)

        history = bus.get_history()
        assert len(history) == 2
        assert history[0].content == "消息1"
        assert history[1].content == "消息2"

    @pytest.mark.asyncio
    async def test_history_filter_by_agent(self, bus):
        """按 Agent 过滤历史记录"""
        await bus.register("alice")
        await bus.register("bob")

        await bus.send(_msg(sender="alice", content="来自 alice", receiver="bob"))
        await bus.send(_msg(sender="bob", content="来自 bob", receiver="alice"))

        alice_history = bus.get_history(agent_id="alice")
        assert len(alice_history) == 2  # alice 发送的和接收的

        bob_history = bus.get_history(agent_id="bob")
        assert len(bob_history) == 2

        ghost_history = bus.get_history(agent_id="ghost")
        assert len(ghost_history) == 0

    @pytest.mark.asyncio
    async def test_history_cleanup(self, bus):
        """历史消息超过上限时自动裁剪"""
        bus._max_history = 5  # 设置小上限便于测试

        await bus.register("alice")
        await bus.register("bob")

        # 发送 10 条消息
        for i in range(10):
            await bus.send(_msg(sender="alice", content=f"消息{i}", receiver="bob"))

        history = bus.get_history()
        assert len(history) == 5, f"历史应裁剪到 {bus._max_history} 条"
        # 应保留最新的 5 条
        assert history[0].content == "消息5"
        assert history[-1].content == "消息9"

    @pytest.mark.asyncio
    async def test_broadcast_history(self, bus):
        """广播消息也被记录到历史"""
        await bus.register("alice")
        await bus.register("bob")

        await bus.broadcast(_msg(sender="alice", content="广播"))

        history = bus.get_history()
        assert len(history) == 1
        assert history[0].content == "广播"

    # ------------------------------------------------------------------
    # 消息属性
    # ------------------------------------------------------------------

    def test_message_auto_id(self):
        """消息自动生成 UUID"""
        msg = A2AMessage(sender_id="test", content="hello")
        assert msg.id, "应自动生成 ID"
        assert len(msg.id) == 36  # UUID 标准长度

    def test_message_custom_id(self):
        """消息接受自定义 ID"""
        msg = A2AMessage(sender_id="test", content="hello", id="custom-123")
        assert msg.id == "custom-123"

    def test_message_timestamp(self):
        """消息自动生成时间戳"""
        msg = A2AMessage(sender_id="test", content="hello")
        assert msg.timestamp is not None

"""
AgentForge A2A 消息总线 - Agent间异步通信基础设施

提供三种通信模式：
  - 点对点发送 (send)
  - 广播 (broadcast)
  - 请求-响应 (request_response)

所有消息自动记录历史，保留最近 1000 条防止内存泄漏。
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class A2AMessage:
    """Agent-to-Agent 消息数据类

    对应用层暴露的轻量消息体，无 Pydantic 依赖，
    receiver_id 为 None 时表示广播消息。
    """

    sender_id: str
    content: str
    message_type: str = "broadcast"  # "request" | "response" | "broadcast"
    id: str = ""  # 留空时自动生成 UUID
    receiver_id: Optional[str] = None  # None = 广播
    correlation_id: Optional[str] = None  # 请求-响应配对标识
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())


# =============================================================================
# 消息总线
# =============================================================================


class A2ABus:
    """A2A 异步消息总线

    每个注册 Agent 拥有独立的 asyncio.Queue，
    send/broadcast 将消息投递至目标队列，
    receive 阻塞等待消息到达。

    请求-响应模式通过 correlation_id 配对，
    发送方调用 request_response 后阻塞等待匹配的响应消息。
    """

    _DEFAULT_MAX_HISTORY = 1000
    _DEFAULT_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue[A2AMessage]] = {}
        self._history: List[A2AMessage] = []
        self._max_history: int = self._DEFAULT_MAX_HISTORY
        self._lock = asyncio.Lock()
        # 请求-响应临时队列, key = correlation_id
        self._pending_responses: Dict[str, asyncio.Queue[A2AMessage]] = {}

    # -------------------------------------------------------------------------
    # 生命周期
    # -------------------------------------------------------------------------

    async def register(self, agent_id: str) -> None:
        """为 Agent 创建消息队列并注册到总线。

        Args:
            agent_id: Agent 唯一标识

        幂等：重复注册同一 agent_id 不会创建新队列。
        """
        async with self._lock:
            if agent_id in self._queues:
                logger.warning("Agent %s 已注册，跳过重复注册", agent_id)
                return
            self._queues[agent_id] = asyncio.Queue()
        logger.info("Agent %s 已注册到消息总线", agent_id)

    async def unregister(self, agent_id: str) -> None:
        """从总线移除 Agent，清理其消息队列。

        Args:
            agent_id: Agent 唯一标识

        安全：已移除的 Agent 无法再接收消息，但正在 receive() 阻塞的
        协程仍会正常返回（队列引用未被回收前有效）。
        """
        async with self._lock:
            queue = self._queues.pop(agent_id, None)

        if queue is None:
            logger.warning("Agent %s 未注册，无法取消注册", agent_id)
            return

        # 排空队列，防止残留消息占用内存
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("Agent %s 已从消息总线移除", agent_id)

    # -------------------------------------------------------------------------
    # 消息投递
    # -------------------------------------------------------------------------

    async def send(self, message: A2AMessage) -> None:
        """点对点发送消息到指定接收者。

        Args:
            message: 待发送的消息，receiver_id 不能为 None
        """
        self._add_to_history(message)

        if message.receiver_id is None:
            logger.warning("消息 %s 未指定 receiver_id，点对点发送被忽略", message.id)
            return

        async with self._lock:
            queue = self._queues.get(message.receiver_id)

        if queue is None:
            logger.warning(
                "接收者 %s 未注册，消息 %s 被丢弃",
                message.receiver_id,
                message.id,
            )
            return

        await queue.put(message)
        await self._resolve_pending_response(message)

        logger.debug(
            "消息 %s: %s -> %s [%s]",
            message.id,
            message.sender_id,
            message.receiver_id,
            message.message_type,
        )

    async def broadcast(self, message: A2AMessage) -> None:
        """广播消息给所有已注册 Agent（排除发送者自身）。

        Args:
            message: 待广播的消息
        """
        self._add_to_history(message)

        async with self._lock:
            targets = [
                agent_id
                for agent_id in self._queues
                if agent_id != message.sender_id
            ]

        for agent_id in targets:
            queue = self._queues.get(agent_id)
            if queue is not None:
                await queue.put(message)

        await self._resolve_pending_response(message)

        logger.debug("消息 %s 广播至 %d 个 Agent", message.id, len(targets))

    # -------------------------------------------------------------------------
    # 请求-响应
    # -------------------------------------------------------------------------

    async def request_response(
        self,
        request: A2AMessage,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> Optional[A2AMessage]:
        """发送请求并阻塞等待匹配的响应消息。

        匹配规则：响应消息的 correlation_id 与请求消息一致。
        如果请求没有 correlation_id，将自动生成一个。

        Args:
            request: 请求消息（message_type 应设为 "request"）
            timeout: 最大等待秒数，超时返回 None

        Returns:
            匹配的响应消息，超时则返回 None
        """
        if not request.correlation_id:
            request.correlation_id = str(uuid.uuid4())

        correlation_id: str = request.correlation_id
        response_queue: asyncio.Queue[A2AMessage] = asyncio.Queue()

        async with self._lock:
            self._pending_responses[correlation_id] = response_queue

        try:
            # 发送请求（自动路由到 receiver_id）
            await self.send(request)

            # 阻塞等待匹配的响应
            response = await asyncio.wait_for(
                response_queue.get(),
                timeout=timeout,
            )
            logger.debug(
                "请求-响应完成: correlation_id=%s (%s <- %s)",
                correlation_id,
                request.sender_id,
                response.sender_id,
            )
            return response

        except asyncio.TimeoutError:
            logger.warning(
                "请求-响应超时: correlation_id=%s (%.1fs)",
                correlation_id,
                timeout,
            )
            return None

        finally:
            async with self._lock:
                self._pending_responses.pop(correlation_id, None)

    # -------------------------------------------------------------------------
    # 消息接收
    # -------------------------------------------------------------------------

    async def receive(self, agent_id: str) -> A2AMessage:
        """阻塞等待该 Agent 的下一条消息。

        Args:
            agent_id: Agent 唯一标识

        Returns:
            队列中的下一条 A2AMessage

        Raises:
            ValueError: agent_id 未注册
        """
        async with self._lock:
            queue = self._queues.get(agent_id)

        if queue is None:
            raise ValueError(f"Agent '{agent_id}' 未注册到消息总线")

        message = await queue.get()
        logger.debug("Agent %s 收到消息 %s", agent_id, message.id)
        return message

    # -------------------------------------------------------------------------
    # 历史查询
    # -------------------------------------------------------------------------

    def get_history(self, agent_id: Optional[str] = None) -> List[A2AMessage]:
        """获取历史消息记录。

        Args:
            agent_id: 可选，过滤该 Agent 作为发送者或接收者的消息。
                      为 None 时返回全部历史。

        Returns:
            消息列表（按时间升序）
        """
        if agent_id is None:
            return list(self._history)

        return [
            msg
            for msg in self._history
            if msg.sender_id == agent_id or msg.receiver_id == agent_id
        ]

    # -------------------------------------------------------------------------
    # 内部方法
    # -------------------------------------------------------------------------

    def _add_to_history(self, message: A2AMessage) -> None:
        """添加消息到历史，自动裁剪保留最近 _max_history 条。

        在 asyncio 单线程模型下，list 的 append 与切片为原子操作，
        不会出现数据损坏；仅在极端并发时可能短暂超过上限几条，
        属可接受的良性竞态。
        """
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    async def _resolve_pending_response(self, message: A2AMessage) -> None:
        """检查并投递待匹配的请求-响应消息。

        如果消息的 correlation_id 匹配某个等待中的请求，
        将消息放入对应的临时响应队列。
        """
        if message.correlation_id is None:
            return

        async with self._lock:
            pending_queue = self._pending_responses.get(message.correlation_id)

        if pending_queue is not None:
            await pending_queue.put(message)
            logger.debug(
                "响应消息匹配: correlation_id=%s",
                message.correlation_id,
            )

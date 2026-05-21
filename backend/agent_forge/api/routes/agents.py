"""
AgentForge Agent 管理 API 路由

提供 Agent 状态查询、消息发送和 SSE 实时流。
所有端点前缀: /api/v1/agents
"""
import asyncio
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.core.a2a_bus import A2ABus, A2AMessage
from agent_forge.database.connection import get_db
from agent_forge.database.models import AgentStateORM
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["agents"])

# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------

_a2a_bus = A2ABus()

# Agent 状态 SSE 广播队列列表
_agent_sse_queues: List[asyncio.Queue] = []


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------


class MessageRequest(BaseModel):
    """发送消息给 Agent 的请求体"""
    content: str
    message_type: str = "broadcast"  # broadcast / request / response


class AgentResponse(BaseModel):
    """Agent 状态响应体"""
    id: str
    role: str
    name: str
    status: str
    current_task_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentMessageResponse(BaseModel):
    """Agent 消息响应体"""
    id: str
    sender_id: str
    receiver_id: Optional[str] = None
    message_type: str
    content: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _orm_agent_to_response(agent: AgentStateORM) -> AgentResponse:
    """将 AgentState ORM 模型转换为响应模型"""
    return AgentResponse(
        id=agent.id,
        role=agent.role,
        name=agent.name,
        status=agent.status,
        current_task_id=agent.current_task_id,
        created_at=agent.created_at,
    )


async def _a2a_message_to_response(msg: A2AMessage) -> AgentMessageResponse:
    """将 A2A 消息转换为响应模型"""
    return AgentMessageResponse(
        id=msg.id,
        sender_id=msg.sender_id,
        receiver_id=msg.receiver_id,
        message_type=msg.message_type,
        content=msg.content,
        timestamp=msg.timestamp,
    )


async def _broadcast_agent_state(agent: AgentStateORM) -> None:
    """向所有 Agent SSE 订阅者广播 Agent 状态变更

    Args:
        agent: Agent 状态 ORM 实例
    """
    if not _agent_sse_queues:
        return

    payload = _orm_agent_to_response(agent)
    data = payload.model_dump_json()
    dead_queues: List[asyncio.Queue] = []

    for q in _agent_sse_queues:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            dead_queues.append(q)

    # 清理已满的队列（订阅者可能已断开）
    for q in dead_queues:
        if q in _agent_sse_queues:
            _agent_sse_queues.remove(q)


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------


@router.get("/stream")
async def stream_agents(
    request: Request,
) -> StreamingResponse:
    """SSE Agent 状态实时流

    当 Agent 状态发生变更时实时推送给前端。

    注意: 此端点必须定义在 /{agent_id} 之前，
    防止 "stream" 被匹配为 agent_id 参数。
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _agent_sse_queues.append(queue)

    async def _event_generator():
        """SSE 事件生成器"""
        try:
            # 首先发送当前所有 Agent 的状态快照
            async with _create_session() as db:
                result = await db.execute(select(AgentStateORM))
                agents = result.scalars().all()
                for agent in agents:
                    resp = _orm_agent_to_response(agent)
                    yield f"event: agent_state\ndata: {resp.model_dump_json()}\n\n"

            # 等待实时状态变更事件
            while True:
                if await request.is_disconnected():
                    break

                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: agent_state\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

        except asyncio.CancelledError:
            logger.debug("Agent SSE 流被取消")
        finally:
            if queue in _agent_sse_queues:
                _agent_sse_queues.remove(queue)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
) -> List[AgentResponse]:
    """查询所有 Agent 状态

    按创建时间升序排列。
    """
    result = await db.execute(
        select(AgentStateORM).order_by(AgentStateORM.created_at.asc())
    )
    agents = result.scalars().all()
    return [_orm_agent_to_response(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """查询 Agent 详情

    Args:
        agent_id: Agent 唯一标识

    Raises:
        HTTPException: 404 当 Agent 不存在时
    """
    agent = await db.get(AgentStateORM, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent 不存在: {agent_id}")
    return _orm_agent_to_response(agent)


@router.post("/{agent_id}/message", response_model=AgentMessageResponse, status_code=201)
async def send_agent_message(
    agent_id: str,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentMessageResponse:
    """发送消息给指定 Agent

    通过 A2A 消息总线将消息投递至目标 Agent 的消息队列。

    Args:
        agent_id: 目标 Agent ID
        body: 消息内容及类型
        db: 数据库会话

    Raises:
        HTTPException: 404 当 Agent 不存在时
    """
    # 验证 Agent 是否存在
    agent = await db.get(AgentStateORM, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent 不存在: {agent_id}")

    # 确保 Agent 已在 A2A 总线注册
    try:
        await _a2a_bus.register(agent_id)
    except Exception:
        logger.warning("Agent %s 注册 A2A 总线时出现警告", agent_id)

    # 构造并发送消息
    message = A2AMessage(
        sender_id="api",
        receiver_id=agent_id,
        content=body.content,
        message_type=body.message_type,
    )

    await _a2a_bus.send(message)
    logger.info(
        "消息已发送: api → %s (type=%s)", agent_id, body.message_type
    )

    return await _a2a_message_to_response(message)


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _create_session():
    """为 SSE 生成器内部使用创建独立数据库会话"""
    from agent_forge.database.connection import async_session as _async_session
    return _async_session()

"""
AgentForge 任务管理 API 路由

提供任务的 CRUD 操作和 SSE 实时流。
所有端点前缀: /api/v1/tasks
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.api.responses import success_response
from agent_forge.core.cancellation import CancellationToken
from agent_forge.core.llm_client import LLMRouter
from agent_forge.core.orchestrator import Orchestrator
from agent_forge.core.planner import Planner
from agent_forge.database.connection import get_db
from agent_forge.database.models import StepORM, TaskORM
from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.models.schemas import AgentStep, TaskStatus
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["tasks"])

# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------

_llm_router = LLMRouter()
_tool_registry = ToolRegistry()
_planner = Planner(_llm_router)
_orchestrator = Orchestrator(_llm_router, _tool_registry)

# 取消令牌映射: task_id → CancellationToken
_cancel_tokens: Dict[str, CancellationToken] = {}


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------


class CreateTaskRequest(BaseModel):
    """创建任务请求体"""
    title: str
    description: str


class TaskResponse(BaseModel):
    """任务响应体"""
    id: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StepResponse(BaseModel):
    """步骤响应体"""
    id: str
    task_id: str
    agent_id: str
    agent_role: str
    step_type: str
    content: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class TaskDetailResponse(TaskResponse):
    """任务详情响应体（含步骤列表）"""
    steps: List[StepResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _orm_task_to_response(task: TaskORM) -> TaskResponse:
    """将 ORM 模型转换为响应模型"""
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _orm_step_to_response(step: StepORM) -> StepResponse:
    """将步骤 ORM 模型转换为响应模型"""
    return StepResponse(
        id=step.id,
        task_id=step.task_id,
        agent_id=step.agent_id,
        agent_role=step.agent_role,
        step_type=step.step_type,
        content=step.content,
        timestamp=step.timestamp,
    )


async def _save_step(
    db: AsyncSession,
    step: AgentStep,
    task_id: str,
) -> StepORM:
    """将 AgentStep 保存到数据库

    Args:
        db: 数据库会话
        step: Agent 执行步骤
        task_id: 关联的任务 ID

    Returns:
        保存后的 StepORM 实例
    """
    step_orm = StepORM(
        id=step.id,
        task_id=task_id,
        agent_id=step.agent_id,
        agent_role=(
            step.agent_role.value
            if hasattr(step.agent_role, "value")
            else str(step.agent_role)
        ),
        step_number=step.step_number,
        step_type=(
            step.step_type.value
            if hasattr(step.step_type, "value")
            else str(step.step_type)
        ),
        content=step.content,
        timestamp=step.timestamp,
    )
    db.add(step_orm)
    await db.commit()
    await db.refresh(step_orm)
    return step_orm


async def _background_execute(
    task_id: str,
    task_description: str,
):
    """后台执行任务

    1. 调用 Planner 生成 PlanGraph
    2. 调用 Orchestrator 执行计划
    3. 每一步产出后写入数据库
    4. 完成/失败后更新任务状态

    Args:
        task_id: 任务 ID
        task_description: 任务描述
    """
    cancel_token = _cancel_tokens.get(task_id, CancellationToken())

    try:
        # 1. 规划
        logger.info("开始规划任务 %s", task_id)
        plan = await _planner.plan(task_description)

        # 2. 更新任务状态为 executing
        from agent_forge.database.connection import async_session

        async with async_session() as db:
            task = await db.get(TaskORM, task_id)
            if task:
                task.status = TaskStatus.EXECUTING.value
                task.updated_at = datetime.now(timezone.utc)
                await db.commit()

        # 3. 执行并持久化步骤
        async for step in _orchestrator.execute_plan(plan, cancel_token):
            async with async_session() as db:
                await _save_step(db, step, task_id)
                # 广播步骤事件到 SSE 队列
                await _broadcast_step(task_id, step)

        # 4. 更新任务状态为 completed
        async with async_session() as db:
            task = await db.get(TaskORM, task_id)
            if task:
                task.status = TaskStatus.COMPLETED.value
                task.updated_at = datetime.now(timezone.utc)
                await db.commit()
            logger.info("任务 %s 执行完成", task_id)

    except asyncio.CancelledError:
        logger.warning("任务 %s 被取消", task_id)
        async with async_session() as db:
            task = await db.get(TaskORM, task_id)
            if task:
                task.status = TaskStatus.CANCELLED.value
                task.updated_at = datetime.now(timezone.utc)
                await db.commit()

    except Exception as e:
        logger.exception("任务 %s 执行失败: %s", task_id, e)
        async with async_session() as db:
            task = await db.get(TaskORM, task_id)
            if task:
                task.status = TaskStatus.FAILED.value
                task.updated_at = datetime.now(timezone.utc)
                await db.commit()


# ---------------------------------------------------------------------------
# SSE 事件队列管理
# ---------------------------------------------------------------------------

# 每个任务维护一个事件队列列表，用于 SSE 广播
_sse_queues: Dict[str, List[asyncio.Queue]] = {}


async def _broadcast_step(task_id: str, step: AgentStep) -> None:
    """向该任务的所有 SSE 订阅者广播步骤事件

    Args:
        task_id: 任务 ID
        step: Agent 执行步骤
    """
    queues = _sse_queues.get(task_id, [])
    if not queues:
        return

    data = json.dumps(
        {
            "type": "step_update",
            "step": jsonable_encoder(step),
        },
        default=str,
    )
    for q in queues:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            logger.warning("SSE 队列已满，丢弃事件: task_id=%s", task_id)


def _subscribe_sse(task_id: str) -> asyncio.Queue:
    """为任务创建 SSE 事件订阅

    Args:
        task_id: 任务 ID

    Returns:
        异步队列，用于接收 SSE 事件
    """
    if task_id not in _sse_queues:
        _sse_queues[task_id] = []
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    _sse_queues[task_id].append(q)
    return q


def _unsubscribe_sse(task_id: str, queue: asyncio.Queue) -> None:
    """取消 SSE 事件订阅

    Args:
        task_id: 任务 ID
        queue: 待移除的队列
    """
    queues = _sse_queues.get(task_id, [])
    if queue in queues:
        queues.remove(queue)
    if not queues:
        _sse_queues.pop(task_id, None)


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------


@router.post("/", response_model=None, status_code=201)
async def create_task(
    body: CreateTaskRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建新任务

    1. 保存任务记录到数据库
    2. 调用 Planner 拆解任务
    3. 启动 Orchestrator 后台执行
    4. 返回任务基本信息
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 创建取消令牌
    cancel_token = CancellationToken()
    _cancel_tokens[task_id] = cancel_token

    # 创建 ORM 实例并保存
    task_orm = TaskORM(
        id=task_id,
        title=body.title,
        description=body.description,
        status=TaskStatus.PENDING.value,
        created_at=now,
    )
    db.add(task_orm)
    await db.commit()
    await db.refresh(task_orm)

    logger.info("任务已创建: %s - %s", task_id, body.title)

    # 更新状态为 planning
    task_orm.status = TaskStatus.PLANNING.value
    task_orm.updated_at = now
    await db.commit()
    await db.refresh(task_orm)

    # 启动后台执行（非阻塞）
    asyncio.create_task(
        _background_execute(task_id, body.description)
    )

    return success_response(_orm_task_to_response(task_orm))


@router.get("/", response_model=None)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
):
    """查询所有任务

    按创建时间降序排列。
    """
    result = await db.execute(
        select(TaskORM).order_by(TaskORM.created_at.desc())
    )
    tasks = result.scalars().all()
    return success_response([_orm_task_to_response(t) for t in tasks])


@router.get("/{task_id}", response_model=None)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """查询任务详情（含执行步骤）

    Args:
        task_id: 任务 ID

    Raises:
        HTTPException: 404 当任务不存在时
    """
    # 查询任务
    task = await db.get(TaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 查询关联步骤
    steps_result = await db.execute(
        select(StepORM)
        .where(StepORM.task_id == task_id)
        .order_by(StepORM.step_number.asc())
    )
    steps = steps_result.scalars().all()

    return success_response(
        TaskDetailResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            steps=[_orm_step_to_response(s) for s in steps],
        )
    )


@router.delete("/{task_id}", status_code=204)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """取消任务

    通过 CancellationToken 通知正在执行的任务停止。

    Args:
        task_id: 任务 ID

    Raises:
        HTTPException: 404 当任务不存在时
    """
    task = await db.get(TaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 发送取消信号
    cancel_token = _cancel_tokens.get(task_id)
    if cancel_token:
        await cancel_token.cancel(f"用户取消任务 {task_id}")
    else:
        logger.warning("任务 %s 无对应的取消令牌", task_id)

    # 更新任务状态
    task.status = TaskStatus.CANCELLED.value
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("任务 %s 已被取消", task_id)


@router.get("/{task_id}/stream")
async def stream_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE 实时流

    订阅任务执行过程，实时推送每步结果。

    SSE 事件格式:
        event: step
        data: {"id": "...", ...}

    Args:
        task_id: 任务 ID
        request: FastAPI Request 对象（用于检测客户端断开）
        db: 数据库会话

    Raises:
        HTTPException: 404 当任务不存在时
    """
    # 验证任务存在
    task = await db.get(TaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    queue = _subscribe_sse(task_id)

    async def _event_generator():
        """SSE 事件生成器"""
        try:
            # 首先发送当前已有的步骤（历史回放）
            async with _create_session() as hist_db:
                result = await hist_db.execute(
                    select(StepORM)
                    .where(StepORM.task_id == task_id)
                    .order_by(StepORM.step_number.asc())
                )
                existing_steps = result.scalars().all()
                for step_orm in existing_steps:
                    step_resp = _orm_step_to_response(step_orm)
                    payload = json.dumps(
                        {
                            "type": "step_update",
                            "step": jsonable_encoder(step_resp),
                        },
                        default=str,
                    )
                    yield f"event: step\ndata: {payload}\n\n"

            # 然后等待实时事件
            while True:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break

                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: step\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield ": heartbeat\n\n"

                # 检查任务是否已完成
                async with _create_session() as status_db:
                    current_task = await status_db.get(TaskORM, task_id)
                    if current_task and current_task.status in (
                        TaskStatus.COMPLETED.value,
                        TaskStatus.FAILED.value,
                        TaskStatus.CANCELLED.value,
                    ):
                        task_payload = json.dumps(
                            {
                                "type": "done",
                                "status": current_task.status,
                                "task": jsonable_encoder(
                                    _orm_task_to_response(current_task)
                                ),
                            },
                            default=str,
                        )
                        yield f"event: done\ndata: {task_payload}\n\n"
                        break

        except asyncio.CancelledError:
            logger.debug("SSE 流被取消: task_id=%s", task_id)
        finally:
            _unsubscribe_sse(task_id, queue)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _create_session():
    """为 SSE 生成器内部使用创建独立数据库会话"""
    from agent_forge.database.connection import async_session as _async_session
    return _async_session()

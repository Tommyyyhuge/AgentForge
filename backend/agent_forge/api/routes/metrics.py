"""
AgentForge 性能指标 API 路由

提供系统性能指标的查询接口。
所有端点前缀: /api/v1/metrics
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.api.middleware.auth import get_current_active_user
from agent_forge.api.responses import success_response
from agent_forge.core.metrics_service import MetricsService
from agent_forge.database.connection import get_db
from agent_forge.database.models import UserORM
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


# ============================================================
# 响应模型
# ============================================================

class TaskMetricsResponse(BaseModel):
    timestamps: list[str]
    durations: list[float]
    counts: list[int]


class AgentMetricsResponse(BaseModel):
    name: str
    calls: int
    avgDuration: int


class TokenMetricsResponse(BaseModel):
    timestamps: list[str]
    inputTokens: list[int]
    outputTokens: list[int]


class SystemMetricsResponse(BaseModel):
    cpuUsage: float
    memoryUsage: float
    activeTasks: int
    totalRequests: int


# ============================================================
# API 端点
# ============================================================

@router.get(
    "/tasks",
    response_model=None,
    summary="任务执行时间趋势",
)
async def get_task_metrics(
    range_hours: Optional[int] = Query(default=24, ge=1, le=168, description="时间范围（小时）"),
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务执行时间趋势
    
    返回指定时间范围内的任务执行时间趋势数据。
    """
    logger.info(f"用户 {user.username} 查询任务指标，时间范围: {range_hours}h")
    data = await MetricsService.get_task_metrics(db, range_hours or 24)
    return success_response(TaskMetricsResponse(**data))


@router.get(
    "/agents",
    response_model=None,
    summary="Agent 调用分布",
)
async def get_agent_metrics(
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Agent 调用分布
    
    返回各 Agent 的调用次数和平均执行时间。
    """
    logger.info(f"用户 {user.username} 查询 Agent 指标")
    data = await MetricsService.get_agent_metrics(db)
    return success_response([AgentMetricsResponse(**item) for item in data])


@router.get(
    "/tokens",
    response_model=None,
    summary="Token 消耗趋势",
)
async def get_token_metrics(
    range_hours: Optional[int] = Query(default=24, ge=1, le=168, description="时间范围（小时）"),
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Token 消耗趋势
    
    返回指定时间范围内的 Token 消耗数据。
    """
    logger.info(f"用户 {user.username} 查询 Token 指标，时间范围: {range_hours}h")
    data = await MetricsService.get_token_metrics(db, range_hours or 24)
    return success_response(TokenMetricsResponse(**data))


@router.get(
    "/system",
    response_model=None,
    summary="系统资源使用",
)
async def get_system_metrics(
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取系统资源使用情况
    
    返回 CPU、内存等系统资源使用情况。
    """
    logger.info(f"用户 {user.username} 查询系统指标")
    data = await MetricsService.get_system_metrics(db)
    return success_response(SystemMetricsResponse(**data))

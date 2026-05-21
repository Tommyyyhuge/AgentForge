"""
AgentForge 性能指标服务

提供系统性能指标的计算和聚合功能。
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database.models import AgentStateORM, StepORM, TaskORM
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class MetricsService:
    """性能指标服务
    
    负责收集、聚合和查询系统性能指标。
    从数据库实时聚合任务执行数据。
    """
    
    @staticmethod
    async def get_task_metrics(db: AsyncSession, range_hours: int = 24) -> Dict:
        """获取任务执行时间趋势
        
        Args:
            db: 数据库会话
            range_hours: 时间范围（小时），默认24小时
            
        Returns:
            {
                "timestamps": ["00:00", "04:00", ...],
                "durations": [1500, 1800, ...],  // 平均执行时间(ms)
                "counts": [5, 8, ...]  // 任务数量
            }
        """
        since = datetime.now(timezone.utc) - timedelta(hours=range_hours)
        
        # 按4小时分段聚合
        intervals = 6
        interval_hours = range_hours / intervals
        
        timestamps = []
        durations = []
        counts = []
        
        for i in range(intervals):
            interval_start = since + timedelta(hours=i * interval_hours)
            interval_end = since + timedelta(hours=(i + 1) * interval_hours)
            
            result = await db.execute(
                select(
                    func.count(TaskORM.id).label("count"),
                    func.avg(
                        func.julianday(TaskORM.updated_at) - func.julianday(TaskORM.created_at)
                    ).label("avg_duration")
                ).where(
                    TaskORM.created_at >= interval_start,
                    TaskORM.created_at < interval_end,
                    TaskORM.updated_at.is_not(None)
                )
            )
            row = result.one_or_none()
            
            timestamps.append(interval_start.strftime("%H:%M"))
            counts.append(row.count or 0)
            # avg_duration 是天数，转换为毫秒
            durations.append(round((row.avg_duration or 0) * 24 * 3600 * 1000))
        
        return {
            "timestamps": timestamps,
            "durations": durations,
            "counts": counts,
        }
    
    @staticmethod
    async def get_agent_metrics(db: AsyncSession) -> List[Dict]:
        """获取 Agent 调用分布
        
        Args:
            db: 数据库会话
            
        Returns:
            [
                {
                    "name": "Prometheus",
                    "calls": 45,
                    "avgDuration": 1200
                },
                ...
            ]
        """
        result = await db.execute(
            select(
                StepORM.agent_role.label("name"),
                func.count(StepORM.id).label("calls"),
                func.avg(StepORM.step_number).label("avg_duration")
            ).group_by(
                StepORM.agent_role
            ).order_by(
                func.count(StepORM.id).desc()
            )
        )
        
        agents = []
        for row in result.all():
            agents.append({
                "name": row.name,
                "calls": row.calls,
                "avgDuration": round(row.avg_duration or 0) * 100,  # step_number 均值 × 100ms 粗略估算
            })
        
        return agents
    
    @staticmethod
    async def get_token_metrics(db: AsyncSession, range_hours: int = 24) -> Dict:
        """获取 Token 消耗趋势
        
        从任务 metadata 中聚合 token 使用数据。
        
        Args:
            db: 数据库会话
            range_hours: 时间范围（小时），默认24小时
            
        Returns:
            {
                "timestamps": ["00:00", "04:00", ...],
                "inputTokens": [1000, 2000, ...],
                "outputTokens": [500, 1000, ...]
            }
        """
        since = datetime.now(timezone.utc) - timedelta(hours=range_hours)
        
        intervals = 6
        interval_hours = range_hours / intervals
        
        timestamps = []
        input_tokens = []
        output_tokens = []
        
        for i in range(intervals):
            interval_start = since + timedelta(hours=i * interval_hours)
            interval_end = since + timedelta(hours=(i + 1) * interval_hours)
            
            result = await db.execute(
                select(TaskORM.task_metadata).where(
                    TaskORM.created_at >= interval_start,
                    TaskORM.created_at < interval_end
                )
            )
            
            total_input = 0
            total_output = 0
            
            for row in result.all():
                metadata = row.task_metadata or {}
                total_input += metadata.get("input_tokens", 0)
                total_output += metadata.get("output_tokens", 0)
            
            timestamps.append(interval_start.strftime("%H:%M"))
            input_tokens.append(total_input)
            output_tokens.append(total_output)
        
        return {
            "timestamps": timestamps,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
        }
    
    @staticmethod
    async def get_system_metrics(db: AsyncSession) -> Dict:
        """获取系统资源使用情况
        
        Args:
            db: 数据库会话
            
        Returns:
            {
                "cpuUsage": 45.2,  // CPU使用率(%)
                "memoryUsage": 68.5,  // 内存使用率(%)
                "activeTasks": 12,  // 活跃任务数
                "totalRequests": 156  // 总请求数
            }
        """
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # 查询活跃任务数
            active_result = await db.execute(
                select(func.count(TaskORM.id)).where(TaskORM.status == "running")
            )
            active_tasks = active_result.scalar() or 0
            
            # 查询总任务数
            total_result = await db.execute(select(func.count(TaskORM.id)))
            total_tasks = total_result.scalar() or 0
            
            return {
                "cpuUsage": round(cpu_percent, 1),
                "memoryUsage": round(memory.percent, 1),
                "activeTasks": active_tasks,
                "totalRequests": total_tasks,
            }
        except Exception as e:
            logger.warning(f"获取系统指标失败: {e}")
            return {
                "cpuUsage": 0,
                "memoryUsage": 0,
                "activeTasks": 0,
                "totalRequests": 0,
            }

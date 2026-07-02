"""
AgentForge 性能指标服务

提供系统性能指标的计算和聚合功能。
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from agent_forge.database.models import StepORM, TaskORM
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


def _metric_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _metric_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


class MetricsService:
    """性能指标服务
    
    负责收集、聚合和查询系统性能指标。
    从数据库实时聚合任务执行数据。
    """
    
    @staticmethod
    async def get_task_metrics(
        db: AsyncSession, range_hours: int = 24
    ) -> Dict[str, List[Any]]:
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
            row = result.mappings().one()
            
            timestamps.append(interval_start.strftime("%H:%M"))
            counts.append(row["count"] or 0)
            # avg_duration 是天数，转换为毫秒
            avg_duration = row["avg_duration"] or 0
            durations.append(round(avg_duration * 24 * 3600 * 1000))
        
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
    def _coerce_provider_metric(raw: Any) -> Dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        provider = _metric_text(
            raw.get("provider") or raw.get("providerId") or raw.get("providerType")
        )
        model = _metric_text(raw.get("model") or raw.get("modelId"))
        if not provider or not model:
            return None

        latency_ms = _metric_int(raw.get("latencyMs", raw.get("latency_ms")))
        input_tokens = _metric_int(raw.get("inputTokens", raw.get("input_tokens")))
        output_tokens = _metric_int(raw.get("outputTokens", raw.get("output_tokens")))
        total_tokens = _metric_int(raw.get("totalTokens", raw.get("total_tokens")))
        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens

        error_category = _metric_text(
            raw.get("errorCategory") or raw.get("error_category")
        )
        status = _metric_text(raw.get("status")).lower()
        failed = status in {"failed", "failure", "error"} or bool(error_category)

        return {
            "provider": provider,
            "model": model,
            "latencyMs": latency_ms,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "totalTokens": total_tokens,
            "failed": failed,
            "errorCategory": error_category,
        }

    @staticmethod
    async def get_provider_metrics(
        db: AsyncSession, range_hours: int = 24
    ) -> List[Dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(hours=range_hours)

        result = await db.execute(
            select(TaskORM.task_metadata).where(TaskORM.created_at >= since)
        )

        aggregates: Dict[tuple[str, str], Dict[str, Any]] = {}
        for row in result.all():
            metadata = row.task_metadata or {}
            raw_metrics = metadata.get("provider_metrics", [])
            if not isinstance(raw_metrics, list):
                continue

            for raw_metric in raw_metrics:
                metric = MetricsService._coerce_provider_metric(raw_metric)
                if metric is None:
                    continue

                key = (metric["provider"], metric["model"])
                bucket = aggregates.setdefault(
                    key,
                    {
                        "provider": metric["provider"],
                        "model": metric["model"],
                        "calls": 0,
                        "failures": 0,
                        "inputTokens": 0,
                        "outputTokens": 0,
                        "totalTokens": 0,
                        "_latencyTotal": 0,
                        "_latencyCount": 0,
                        "_errorCategories": {},
                    },
                )

                bucket["calls"] += 1
                bucket["inputTokens"] += metric["inputTokens"]
                bucket["outputTokens"] += metric["outputTokens"]
                bucket["totalTokens"] += metric["totalTokens"]
                if metric["latencyMs"] > 0:
                    bucket["_latencyTotal"] += metric["latencyMs"]
                    bucket["_latencyCount"] += 1
                if metric["failed"]:
                    bucket["failures"] += 1
                if metric["errorCategory"]:
                    errors = bucket["_errorCategories"]
                    errors[metric["errorCategory"]] = (
                        errors.get(metric["errorCategory"], 0) + 1
                    )

        provider_metrics = []
        for bucket in aggregates.values():
            latency_count = bucket.pop("_latencyCount")
            latency_total = bucket.pop("_latencyTotal")
            error_categories = bucket.pop("_errorCategories")
            bucket["avgLatencyMs"] = (
                round(latency_total / latency_count) if latency_count else 0
            )
            bucket["errorCategories"] = [
                {"category": category, "count": count}
                for category, count in sorted(
                    error_categories.items(), key=lambda item: (-item[1], item[0])
                )
            ]
            provider_metrics.append(bucket)

        return sorted(
            provider_metrics,
            key=lambda item: (-item["calls"], item["provider"], item["model"]),
        )

    @staticmethod
    async def append_provider_metric(
        db: AsyncSession,
        task_id: str,
        raw_metric: Dict[str, Any],
    ) -> bool:
        metric = MetricsService._coerce_provider_metric(raw_metric)
        if metric is None:
            return False

        task = await db.get(TaskORM, task_id)
        if task is None:
            return False

        metadata = dict(task.task_metadata or {})
        existing_metrics = metadata.get("provider_metrics")
        provider_metrics = (
            list(existing_metrics) if isinstance(existing_metrics, list) else []
        )
        provider_metrics.append(
            {
                "provider": metric["provider"],
                "model": metric["model"],
                "latencyMs": metric["latencyMs"],
                "inputTokens": metric["inputTokens"],
                "outputTokens": metric["outputTokens"],
                "totalTokens": metric["totalTokens"],
                "status": "failed" if metric["failed"] else "success",
                "errorCategory": metric["errorCategory"] or None,
            }
        )
        metadata["provider_metrics"] = provider_metrics
        task.task_metadata = metadata
        flag_modified(task, "task_metadata")
        await db.commit()
        return True

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

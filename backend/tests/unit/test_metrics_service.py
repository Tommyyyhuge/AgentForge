from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from agent_forge.core.metrics_service import MetricsService
from agent_forge.database.models import TaskORM


@pytest.mark.asyncio
async def test_provider_metrics_aggregates_provider_model_usage(db_session):
    now = datetime.now(timezone.utc)
    suffix = uuid4().hex
    provider = f"openai-{suffix}"
    db_session.add_all(
        [
            TaskORM(
                id=f"task-openai-1-{suffix}",
                title="Successful call",
                description="Records safe provider metrics",
                status="completed",
                created_at=now - timedelta(minutes=5),
                task_metadata={
                    "provider_metrics": [
                        {
                            "provider": provider,
                            "model": "gpt-4o-mini",
                            "latency_ms": 120,
                            "input_tokens": 20,
                            "output_tokens": 30,
                            "total_tokens": 50,
                            "status": "success",
                        }
                    ]
                },
            ),
            TaskORM(
                id=f"task-openai-2-{suffix}",
                title="Failed call",
                description="Records normalized failure",
                status="failed",
                created_at=now - timedelta(minutes=3),
                task_metadata={
                    "provider_metrics": [
                        {
                            "provider": provider,
                            "model": "gpt-4o-mini",
                            "latencyMs": 240,
                            "inputTokens": 10,
                            "outputTokens": 0,
                            "totalTokens": 10,
                            "status": "failed",
                            "errorCategory": "provider_timeout",
                        }
                    ]
                },
            ),
        ]
    )
    await db_session.commit()

    metrics = await MetricsService.get_provider_metrics(db_session)
    metric = next(item for item in metrics if item["provider"] == provider)

    assert metric == {
        "provider": provider,
        "model": "gpt-4o-mini",
        "calls": 2,
        "failures": 1,
        "avgLatencyMs": 180,
        "inputTokens": 30,
        "outputTokens": 30,
        "totalTokens": 60,
        "errorCategories": [
            {"category": "provider_timeout", "count": 1},
        ],
    }


@pytest.mark.asyncio
async def test_provider_metrics_excludes_sensitive_metadata(db_session):
    now = datetime.now(timezone.utc)
    provider = f"relay-main-{uuid4().hex}"
    db_session.add(
        TaskORM(
            id=f"task-secret-{uuid4().hex}",
            title="Secret-bearing metadata",
            description="Unsafe fields must not leak",
            status="failed",
            created_at=now,
            task_metadata={
                "provider_metrics": [
                        {
                            "provider": provider,
                        "model": "custom/model",
                        "latency_ms": 99,
                        "status": "failed",
                        "error_category": "provider_auth_failed",
                        "prompt": "private prompt text",
                        "api_key": "sk-secret",
                        "authorization": "Bearer sk-secret",
                        "raw_response": {"message": "contains secret"},
                    }
                ]
            },
        )
    )
    await db_session.commit()

    metrics = await MetricsService.get_provider_metrics(db_session)
    metric = next(item for item in metrics if item["provider"] == provider)

    serialized = str(metric)
    assert "private prompt text" not in serialized
    assert "sk-secret" not in serialized
    assert "raw_response" not in serialized
    assert metric["errorCategories"] == [
        {"category": "provider_auth_failed", "count": 1},
    ]


@pytest.mark.asyncio
async def test_provider_metrics_ignores_tasks_outside_range(db_session):
    now = datetime.now(timezone.utc)
    provider = f"deepseek-{uuid4().hex}"
    db_session.add(
        TaskORM(
            id=f"task-old-{uuid4().hex}",
            title="Old provider call",
            description="Should not count",
            status="completed",
            created_at=now - timedelta(hours=48),
            task_metadata={
                "provider_metrics": [
                        {
                            "provider": provider,
                        "model": "deepseek-chat",
                        "latency_ms": 100,
                        "status": "success",
                    }
                ]
            },
        )
    )
    await db_session.commit()

    metrics = await MetricsService.get_provider_metrics(db_session, range_hours=24)

    assert all(item["provider"] != provider for item in metrics)


@pytest.mark.asyncio
async def test_append_provider_metric_persists_only_safe_fields(db_session):
    task_id = f"task-record-{uuid4().hex}"
    db_session.add(
        TaskORM(
            id=task_id,
            title="Record provider call",
            description="Persists safe provider metrics only",
            status="completed",
            created_at=datetime.now(timezone.utc),
            task_metadata={"provider_metrics": [{"not": "a normalized metric"}]},
        )
    )
    await db_session.commit()

    recorded = await MetricsService.append_provider_metric(
        db_session,
        task_id,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "latencyMs": 88,
            "inputTokens": 7,
            "outputTokens": 9,
            "status": "failed",
            "errorCategory": "provider_rate_limited",
            "prompt": "private prompt",
            "apiKey": "sk-secret",
        },
    )

    task = await db_session.get(TaskORM, task_id)
    assert recorded is True
    assert task is not None
    metric = task.task_metadata["provider_metrics"][-1]
    assert metric == {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "latencyMs": 88,
        "inputTokens": 7,
        "outputTokens": 9,
        "totalTokens": 16,
        "status": "failed",
        "errorCategory": "provider_rate_limited",
    }
    assert "private prompt" not in str(task.task_metadata)
    assert "sk-secret" not in str(task.task_metadata)

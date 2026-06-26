import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from agent_forge.api.middleware.auth import get_password_hash
from agent_forge.api.routes import agents as agent_routes
from agent_forge.api.routes import auth as auth_routes
from agent_forge.api.routes import keys as key_routes
from agent_forge.api.routes import metrics as metric_routes
from agent_forge.api.routes import tasks as task_routes
from agent_forge.database.models import APIKeyORM, AgentStateORM, TaskORM, UserORM
from agent_forge.models.schemas import AgentRole, AgentStep, LoginRequest, StepType, TaskStatus


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.added = []
        self.committed = False

    async def execute(self, _statement):
        return _ScalarResult(self.rows)

    def add(self, row):
        self.added.append(row)
        self.rows.append(row)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_task_list_returns_standard_success_envelope():
    created_at = datetime.now(timezone.utc)
    task = TaskORM(
        id="task-1",
        title="Build the thing",
        description="Implement the current scope",
        status=TaskStatus.PENDING.value,
        created_at=created_at,
    )
    response = await task_routes.list_tasks(db=_FakeSession([task]))

    assert response["success"] is True
    assert response["data"][0]["id"] == "task-1"
    assert response["data"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_auth_login_returns_standard_success_envelope():
    user = UserORM(
        id="user-1",
        username="alice",
        email="alice@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    response = await auth_routes.login(
        user_data=LoginRequest(username="alice", password="password123"),
        db=_FakeSession([user]),
    )

    assert response["success"] is True
    assert response["data"]["token_type"] == "bearer"
    assert response["data"]["access_token"]


@pytest.mark.asyncio
async def test_key_list_returns_standard_success_envelope():
    user = UserORM(
        id="user-1",
        username="alice",
        email="alice@example.com",
        hashed_password="hashed",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    key = APIKeyORM(
        id="key-1",
        user_id=user.id,
        provider="kimi",
        encrypted_key="encrypted",
        masked_key="sk-****-1234",
        permission="write",
        is_active=True,
        usage_count=0,
        created_at=datetime.now(timezone.utc),
    )

    response = await key_routes.list_keys(user=user, db=_FakeSession([key]))

    assert response["success"] is True
    assert response["data"][0]["masked_key"] == "sk-****-1234"


@pytest.mark.asyncio
async def test_metrics_returns_standard_success_envelope(monkeypatch):
    user = UserORM(
        id="user-1",
        username="alice",
        email="alice@example.com",
        hashed_password="hashed",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(
        metric_routes.MetricsService,
        "get_system_metrics",
        AsyncMock(
            return_value={
                "cpuUsage": 1.0,
                "memoryUsage": 2.0,
                "activeTasks": 3,
                "totalRequests": 4,
            }
        ),
    )

    response = await metric_routes.get_system_metrics(
        user=user,
        db=_FakeSession(),
    )

    assert response["success"] is True
    assert response["data"]["activeTasks"] == 3


@pytest.mark.asyncio
async def test_agent_list_bootstraps_builtin_agents_when_table_is_empty():
    db = _FakeSession()
    response = await agent_routes.list_agents(db=db)

    assert response["success"] is True
    assert {agent["role"] for agent in response["data"]} == {
        AgentRole.RESEARCHER.value,
        AgentRole.CODER.value,
        AgentRole.WRITER.value,
        AgentRole.REVIEWER.value,
        AgentRole.EXECUTOR.value,
    }
    assert db.committed is True


@pytest.mark.asyncio
async def test_task_sse_broadcast_wraps_step_update_payload():
    task_routes._sse_queues.clear()
    queue = task_routes._subscribe_sse("task-1")
    try:
        step = AgentStep(
            task_id="task-1",
            agent_id="agent-researcher",
            agent_role=AgentRole.RESEARCHER,
            step_number=1,
            step_type=StepType.THOUGHT,
            content="Thinking",
        )

        await task_routes._broadcast_step("task-1", step)
        payload = json.loads(await asyncio.wait_for(queue.get(), timeout=1))

        assert payload["type"] == "step_update"
        assert payload["step"]["step_type"] == "thought"
        assert payload["step"]["content"] == "Thinking"
    finally:
        task_routes._unsubscribe_sse("task-1", queue)


@pytest.mark.asyncio
async def test_agent_sse_broadcast_wraps_agent_update_payload():
    agent_routes._agent_sse_queues.clear()
    queue = asyncio.Queue(maxsize=256)
    agent_routes._agent_sse_queues.append(queue)
    try:
        agent = AgentStateORM(
            id="agent-researcher",
            role=AgentRole.RESEARCHER.value,
            name="Researcher",
            status="idle",
            created_at=datetime.now(timezone.utc),
        )

        await agent_routes._broadcast_agent_state(agent)
        payload = json.loads(await asyncio.wait_for(queue.get(), timeout=1))

        assert payload["type"] == "agent_update"
        assert payload["agent"]["id"] == "agent-researcher"
        assert payload["agent"]["role"] == "researcher"
    finally:
        agent_routes._agent_sse_queues.clear()

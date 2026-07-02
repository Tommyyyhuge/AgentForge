"""
数据模型模块测试
"""
import uuid
from datetime import datetime

import pytest

from agent_forge.models.schemas import (AgentRole, AgentState, AgentStep,
                                        Message, PlanNode, StepType, Task,
                                        TaskResult, TaskStatus)


class TestTask:
    """测试 Task 模型"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(title="测试任务", description="这是一个测试任务")
        assert task.title == "测试任务"
        assert task.description == "这是一个测试任务"
        assert task.status == TaskStatus.PENDING
        assert task.id is not None
        assert isinstance(task.id, str)
        assert uuid.UUID(task.id)  # 验证是有效的 UUID

    def test_task_default_status(self):
        """测试任务默认状态"""
        task = Task(title="任务", description="描述")
        assert task.status == TaskStatus.PENDING

    def test_task_with_custom_status(self):
        """测试任务自定义状态"""
        task = Task(title="任务", description="描述", status=TaskStatus.EXECUTING)
        assert task.status == TaskStatus.EXECUTING

    def test_task_with_parent(self):
        """测试子任务"""
        parent_id = str(uuid.uuid4())
        task = Task(title="子任务", description="子任务描述", parent_id=parent_id)
        assert task.parent_id == parent_id

    def test_task_with_metadata(self):
        """测试任务元数据"""
        task = Task(
            title="任务",
            description="描述",
            metadata={"priority": "high", "tags": ["test"]},
        )
        assert task.metadata["priority"] == "high"
        assert task.metadata["tags"] == ["test"]

    def test_task_created_at(self):
        """测试任务创建时间"""
        from datetime import UTC

        before = datetime.now(UTC)
        task = Task(title="任务", description="描述")
        after = datetime.now(UTC)
        assert before <= task.created_at <= after


class TestTaskResult:
    """测试 TaskResult 模型"""

    def test_task_result_creation(self):
        """测试任务结果创建"""
        result = TaskResult(
            task_id="task-123", status=TaskStatus.COMPLETED, output="任务完成"
        )
        assert result.task_id == "task-123"
        assert result.status == TaskStatus.COMPLETED
        assert result.output == "任务完成"
        assert result.error_message is None

    def test_task_result_failed(self):
        """测试失败的任务结果"""
        result = TaskResult(
            task_id="task-456", status=TaskStatus.FAILED, error_message="发生错误"
        )
        assert result.status == TaskStatus.FAILED
        assert result.error_message == "发生错误"


class TestAgentStep:
    """测试 AgentStep 模型"""

    def test_agent_step_creation(self):
        """测试步骤创建"""
        step = AgentStep(
            task_id="task-123",
            agent_id="agent-456",
            agent_role=AgentRole.REVIEWER,
            step_number=1,
            step_type=StepType.THOUGHT,
            content="思考内容",
        )
        assert step.task_id == "task-123"
        assert step.agent_role == AgentRole.REVIEWER
        assert step.step_type == StepType.THOUGHT
        assert step.content == "思考内容"

    def test_agent_step_with_tool(self):
        """测试带工具的步骤"""
        step = AgentStep(
            task_id="task-123",
            agent_id="agent-456",
            agent_role=AgentRole.EXECUTOR,
            step_number=2,
            step_type=StepType.ACTION,
            content="执行工具",
            tool_name="calculator",
            tool_input={"expression": "1+1"},
            tool_output="2",
            latency_ms=150,
        )
        assert step.tool_name == "calculator"
        assert step.tool_input == {"expression": "1+1"}
        assert step.tool_output == "2"
        assert step.latency_ms == 150


class TestAgentState:
    """测试 AgentState 模型"""

    def test_agent_state_creation(self):
        """测试状态创建"""
        state = AgentState(agent_id="agent-123", role=AgentRole.CODER, status="idle")
        assert state.agent_id == "agent-123"
        assert state.role == AgentRole.CODER
        assert state.status == "idle"
        assert state.current_task_id is None

    def test_agent_state_busy(self):
        """测试忙碌状态"""
        state = AgentState(
            agent_id="agent-123",
            role=AgentRole.CODER,
            status="busy",
            current_task_id="task-456",
        )
        assert state.status == "busy"
        assert state.current_task_id == "task-456"


class TestMessage:
    """测试 Message 模型"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type="request",
            content="请求内容",
        )
        assert msg.sender_id == "agent-1"
        assert msg.receiver_id == "agent-2"
        assert msg.message_type == "request"
        assert msg.content == "请求内容"

    def test_broadcast_message(self):
        """测试广播消息"""
        msg = Message(
            sender_id="agent-1",
            receiver_id=None,
            message_type="broadcast",
            content="广播内容",
        )
        assert msg.receiver_id is None


class TestPlanNode:
    """测试 PlanNode 模型"""

    def test_plan_node_creation(self):
        """测试计划节点创建"""
        node = PlanNode(
            task_id="task-123",
            description="执行步骤1",
            assigned_agent_role=AgentRole.RESEARCHER,
        )
        assert node.task_id == "task-123"
        assert node.description == "执行步骤1"
        assert node.assigned_agent_role == AgentRole.RESEARCHER
        assert node.status == TaskStatus.PENDING

    def test_plan_node_with_dependencies(self):
        """测试带依赖的节点"""
        node = PlanNode(
            task_id="task-123", description="步骤2", dependencies=["node-1", "node-2"]
        )
        assert len(node.dependencies) == 2
        assert "node-1" in node.dependencies


class TestEnums:
    """测试枚举类型"""

    def test_task_status_values(self):
        """测试任务状态枚举值"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.EXECUTING.value == "executing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_agent_role_values(self):
        """测试 Agent 角色枚举值"""
        assert [role.value for role in AgentRole] == [
            "researcher",
            "coder",
            "writer",
            "reviewer",
            "executor",
        ]
        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.WRITER.value == "writer"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.EXECUTOR.value == "executor"

    def test_planner_is_not_executable_agent_role(self):
        """Planner is a planning component, not an executable Agent role."""
        assert "planner" not in {role.value for role in AgentRole}

    def test_step_type_values(self):
        """测试步骤类型枚举值"""
        assert StepType.THOUGHT.value == "thought"
        assert StepType.ACTION.value == "action"
        assert StepType.OBSERVATION.value == "observation"
        assert StepType.FINAL.value == "final"
        assert StepType.ERROR.value == "error"

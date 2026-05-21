"""
ReAct 引擎模块测试
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_forge.core.cancellation import CancellationError, CancellationToken
from agent_forge.core.error_handler import LLMException
from agent_forge.core.llm_client import LLMResponse
from agent_forge.core.react_loop import ReActLoop, ReActOutput
from agent_forge.models.schemas import StepType


class TestReActOutput:
    """测试 ReActOutput 模型"""

    def test_react_output_creation(self):
        """测试输出创建"""
        output = ReActOutput(
            thought="我需要搜索信息",
            action={"tool_name": "web_search", "parameters": {"query": "test"}},
            is_final=False,
        )
        assert output.thought == "我需要搜索信息"
        assert output.action["tool_name"] == "web_search"
        assert not output.is_final

    def test_react_output_final(self):
        """测试最终输出"""
        output = ReActOutput(thought="已找到答案", is_final=True, final_answer="答案是42")
        assert output.is_final
        assert output.final_answer == "答案是42"


class TestReActLoop:
    """测试 ReActLoop"""

    @pytest.fixture
    def mock_llm_router(self):
        router = MagicMock()
        router.route = AsyncMock(
            return_value=LLMResponse(
                content='{"thought": "思考", "action": {"tool_name": "test_tool", "parameters": {}}, "is_final": false}',
                model="test",
            )
        )
        return router

    @pytest.fixture
    def mock_tool(self):
        tool = MagicMock()
        tool.name = "test_tool"
        tool.get_schema.return_value = {
            "name": "test_tool",
            "description": "测试工具",
            "parameters": {},
        }
        tool.execute = AsyncMock(return_value="工具执行结果")
        return tool

    @pytest.fixture
    def react_loop(self, mock_llm_router, mock_tool):
        return ReActLoop(llm_router=mock_llm_router, tools=[mock_tool], max_steps=5)

    @pytest.mark.asyncio
    async def test_run_with_final_answer(self, react_loop, mock_llm_router):
        """测试带最终答案的执行"""
        mock_llm_router.route = AsyncMock(
            return_value=LLMResponse(
                content='{"thought": "已找到答案", "is_final": true, "final_answer": "最终答案"}',
                model="test",
            )
        )

        steps = []
        async for step in react_loop.run(task="测试任务", task_id="task-123"):
            steps.append(step)

        assert len(steps) == 2  # thought + final
        assert steps[0].step_type == StepType.THOUGHT
        assert steps[1].step_type == StepType.FINAL
        assert steps[1].content == "最终答案"
        assert steps[0].task_id == "task-123"

    @pytest.mark.asyncio
    async def test_run_with_tool_execution(
        self, react_loop, mock_llm_router, mock_tool
    ):
        """测试带工具执行的运行"""
        # 第一次返回需要执行工具
        mock_llm_router.route = AsyncMock(
            return_value=LLMResponse(
                content='{"thought": "需要工具", "action": {"tool_name": "test_tool", "parameters": {}}, "is_final": false}',
                model="test",
            )
        )

        react_loop.max_steps = 2
        steps = []
        async for step in react_loop.run(task="使用工具", task_id="task-456"):
            steps.append(step)

        # 应该有 thought + observation (因为工具执行返回结果)
        assert len(steps) >= 2
        assert steps[0].step_type == StepType.THOUGHT
        assert mock_tool.execute.called

    @pytest.mark.asyncio
    async def test_run_max_steps(self, react_loop, mock_llm_router):
        """测试最大步数限制"""
        mock_llm_router.route = AsyncMock(
            return_value=LLMResponse(
                content='{"thought": "继续思考", "is_final": false}', model="test"
            )
        )

        react_loop.max_steps = 2
        react_loop.max_steps = 2
        steps = []
        async for step in react_loop.run(
            task="使用工具",
            task_id="task-456"
        ):
            steps.append(step)

        # 最后一步应该是 FINAL，提示达到最大步数
        assert steps[-1].step_type == StepType.FINAL

    @pytest.mark.asyncio
    async def test_run_cancellation(self, react_loop):
        """测试取消执行"""
        token = CancellationToken()
        await token.cancel("测试取消")

        with pytest.raises(CancellationError):
            async for step in react_loop.run(
                task="测试", task_id="task-000", cancellation_token=token
            ):
                pass

    @pytest.mark.asyncio
    async def test_run_task_id_propagation(self, react_loop, mock_llm_router):
        """测试 task_id 传递"""
        mock_llm_router.route = AsyncMock(
            return_value=LLMResponse(
                content='{"thought": "测试", "is_final": true, "final_answer": "完成"}',
                model="test",
            )
        )

        steps = []
        async for step in react_loop.run(task="测试", task_id="task-abc"):
            steps.append(step)

        for step in steps:
            assert step.task_id == "task-abc"

    def test_parse_response_json(self, react_loop):
        """测试 JSON 响应解析"""
        content = '{"thought": "思考", "is_final": true, "final_answer": "答案"}'
        result = react_loop._parse_response(content)
        assert result.thought == "思考"
        assert result.is_final
        assert result.final_answer == "答案"

    def test_parse_response_with_code_block(self, react_loop):
        """测试代码块中的 JSON"""
        content = (
            '```json\n{"thought": "思考", "is_final": true, "final_answer": "答案"}\n```'
        )
        result = react_loop._parse_response(content)
        assert result.thought == "思考"
        assert result.is_final

    def test_parse_response_invalid_json(self, react_loop):
        """测试无效 JSON 回退"""
        content = "这不是 JSON"
        result = react_loop._parse_response(content)
        assert result.is_final
        assert result.final_answer == "这不是 JSON"

    @pytest.mark.asyncio
    async def test_get_llm_response_with_retry_success(
        self, react_loop, mock_llm_router
    ):
        """测试重试成功"""
        mock_llm_router.route = AsyncMock(
            return_value=LLMResponse(content="成功", model="test")
        )

        response = await react_loop._get_llm_response_with_retry(
            messages=[{"role": "user", "content": "test"}]
        )
        assert response.content == "成功"

    @pytest.mark.asyncio
    async def test_get_llm_response_with_retry_failure(
        self, react_loop, mock_llm_router
    ):
        """测试重试最终失败"""
        mock_llm_router.route = AsyncMock(side_effect=Exception("API 错误"))

        with pytest.raises(LLMException) as exc_info:
            await react_loop._get_llm_response_with_retry(
                messages=[{"role": "user", "content": "test"}], max_retries=2
            )
        assert "已重试 2 次" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_llm_response_cancellation_not_retried(
        self, react_loop, mock_llm_router
    ):
        """测试取消异常不被重试"""
        mock_llm_router.route = AsyncMock(side_effect=CancellationError("用户取消"))

        with pytest.raises(CancellationError):
            await react_loop._get_llm_response_with_retry(
                messages=[{"role": "user", "content": "test"}]
            )

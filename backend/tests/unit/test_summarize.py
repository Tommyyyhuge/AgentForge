"""
文本摘要工具测试

测试 SummarizeTool 的短文本直通、长文本 LLM 摘要、错误处理等功能。
"""
from unittest.mock import AsyncMock

import pytest

from agent_forge.core.llm_client import LLMResponse
from agent_forge.tools.summarize import SummarizeTool


class TestSummarizeTool:
    """测试文本摘要工具"""

    @pytest.mark.asyncio
    async def test_short_text_pass_through(self):
        """测试短文本（<500字）直接返回，不调用 LLM"""
        tool = SummarizeTool(llm_router=AsyncMock())
        short_text = "这是一段很短的文本。"
        result = await tool.execute(text=short_text)
        assert result == short_text
        # 确认未调用 LLM
        tool._llm_router.route.assert_not_called()

    @pytest.mark.asyncio
    async def test_long_text_summarizes(self):
        """测试长文本调用 LLM 摘要"""
        llm_mock = AsyncMock()
        llm_mock.route = AsyncMock(
            return_value=LLMResponse(
                content="这是摘要结果。",
                model="test-model",
                usage={"total_tokens": 50},
                latency_ms=100,
            )
        )
        tool = SummarizeTool(llm_router=llm_mock)

        # 生成 500 字以上的文本
        long_text = "测试 " * 300  # 约 600 字

        result = await tool.execute(text=long_text, max_length=100)
        assert "摘要结果" in result
        llm_mock.route.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_error_handling(self):
        """测试 LLM 调用失败时的降级处理"""
        llm_mock = AsyncMock()
        llm_mock.route = AsyncMock(side_effect=RuntimeError("LLM 服务不可用"))
        tool = SummarizeTool(llm_router=llm_mock)

        long_text = "需要摘要的文本 " * 200  # 约 600 字

        result = await tool.execute(text=long_text, max_length=100)
        assert "摘要错误" in result or "失败" in result

    @pytest.mark.asyncio
    async def test_empty_text(self):
        """测试空文本处理"""
        tool = SummarizeTool(llm_router=AsyncMock())
        result = await tool.execute(text="")
        assert "不能为空" in result

    @pytest.mark.asyncio
    async def test_max_length_too_small(self):
        """测试摘要长度过小处理"""
        tool = SummarizeTool(llm_router=AsyncMock())
        long_text = "测试文本 " * 300
        result = await tool.execute(text=long_text, max_length=5)
        assert "不能小于" in result

    @pytest.mark.asyncio
    async def test_max_length_too_large(self):
        """测试摘要长度过大处理"""
        tool = SummarizeTool(llm_router=AsyncMock())
        long_text = "测试文本 " * 300
        result = await tool.execute(text=long_text, max_length=20000)
        assert "不能超过" in result

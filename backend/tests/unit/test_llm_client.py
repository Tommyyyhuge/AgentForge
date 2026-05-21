"""
LLM 客户端模块测试
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agent_forge.core.error_handler import LLMException
from agent_forge.core.llm_client import (DeepSeekProvider, KimiProvider,
                                         LLMResponse, LLMRouter, StreamChunk)


class TestLLMResponse:
    """测试 LLMResponse 数据类"""

    def test_llm_response_creation(self):
        """测试响应创建"""
        response = LLMResponse(
            content="测试内容",
            model="moonshot-v1-8k",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            latency_ms=500,
        )
        assert response.content == "测试内容"
        assert response.model == "moonshot-v1-8k"
        assert response.usage["prompt_tokens"] == 10
        assert response.latency_ms == 500

    def test_llm_response_default_usage(self):
        """测试默认 usage"""
        response = LLMResponse(content="内容", model="test")
        assert response.usage == {}
        assert response.latency_ms == 0


class TestStreamChunk:
    """测试 StreamChunk 数据类"""

    def test_stream_chunk_creation(self):
        """测试流式块创建"""
        chunk = StreamChunk(content="Hello")
        assert chunk.content == "Hello"
        assert not chunk.is_finished

    def test_stream_chunk_finished(self):
        """测试完成的流式块"""
        chunk = StreamChunk(content="", is_finished=True)
        assert chunk.is_finished


class TestKimiProvider:
    """测试 KimiProvider"""

    @pytest.fixture
    def provider(self):
        return KimiProvider(api_key="test-key", base_url="https://api.test.com")

    @pytest.mark.asyncio
    async def test_chat_success(self, provider):
        """测试聊天成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "回答"}}],
            "usage": {"prompt_tokens": 10},
        }

        with patch.object(provider.client, "post", return_value=mock_response):
            response = await provider.chat(messages=[{"role": "user", "content": "你好"}])
            assert response.content == "回答"
            assert response.model == "moonshot-v1-8k"

    @pytest.mark.asyncio
    async def test_chat_http_error(self, provider):
        """测试 HTTP 错误"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"

        with patch.object(
            provider.client,
            "post",
            side_effect=httpx.HTTPStatusError(
                "Rate limited", request=MagicMock(), response=mock_response
            ),
        ):
            with pytest.raises(LLMException) as exc_info:
                await provider.chat(messages=[{"role": "user", "content": "test"}])
            assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_request_error(self, provider):
        """测试请求错误"""
        with patch.object(
            provider.client, "post", side_effect=httpx.ConnectError("Connection failed")
        ):
            with pytest.raises(LLMException) as exc_info:
                await provider.chat(messages=[{"role": "user", "content": "test"}])
            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close(self, provider):
        """测试关闭客户端"""
        with patch.object(provider.client, "aclose") as mock_close:
            await provider.close()
            mock_close.assert_called_once()


class TestDeepSeekProvider:
    """测试 DeepSeekProvider"""

    @pytest.fixture
    def provider(self):
        return DeepSeekProvider(api_key="test-key", base_url="https://api.test.com")

    @pytest.mark.asyncio
    async def test_chat_success(self, provider):
        """测试聊天成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "DeepSeek回答"}}],
            "usage": {"total_tokens": 30},
        }

        with patch.object(provider.client, "post", return_value=mock_response):
            response = await provider.chat(messages=[{"role": "user", "content": "测试"}])
            assert response.content == "DeepSeek回答"
            assert response.model == "deepseek-chat"


class TestLLMRouter:
    """测试 LLMRouter"""

    @pytest.fixture
    def router(self):
        router = LLMRouter()
        router.providers = {}
        router.fallback_chain = []
        return router

    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.chat = AsyncMock(
            return_value=LLMResponse(content="测试回答", model="test-model")
        )
        return provider

    def test_register_provider(self, router, mock_provider):
        """测试注册提供商"""
        router.register_provider("test", mock_provider)
        assert "test" in router.providers
        assert "test" in router.fallback_chain

    def test_get_provider_existing(self, router, mock_provider):
        """测试获取已存在的提供商"""
        router.register_provider("test", mock_provider)
        provider = router.get_provider("test")
        assert provider == mock_provider

    def test_get_provider_default(self, router, mock_provider):
        """测试获取默认提供商"""
        router.register_provider("default", mock_provider)
        provider = router.get_provider()
        assert provider == mock_provider

    def test_get_provider_not_found(self, router):
        """测试提供商不存在"""
        with pytest.raises(LLMException) as exc_info:
            router.get_provider()
        assert "没有可用的 LLM 提供商" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route(self, router, mock_provider):
        """测试路由调用"""
        router.register_provider("test", mock_provider)
        response = await router.route(messages=[{"role": "user", "content": "你好"}])
        assert response.content == "测试回答"
        mock_provider.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_with_complexity(self, router, mock_provider):
        """测试按复杂度路由"""
        router.register_provider("test", mock_provider)
        await router.route(
            messages=[{"role": "user", "content": "复杂任务"}], complexity="complex"
        )
        # 验证调用了 chat 方法
        mock_provider.chat.assert_called_once()

    def test_close_all(self, router, mock_provider):
        """测试关闭所有连接"""
        mock_provider.close = AsyncMock()
        router.register_provider("test", mock_provider)
        # close_all 是 async 方法，需要 await
        import asyncio

        asyncio.run(router.close_all())
        mock_provider.close.assert_called_once()

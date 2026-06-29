"""
LLM 客户端模块测试
"""
from unittest.mock import AsyncMock, MagicMock

import agent_forge.core as core_exports
import agent_forge.core.llm_client as llm_client_module
import pytest

from agent_forge.core.error_handler import LLMException
from agent_forge.core.llm_client import (LLMResponse, LLMRouter,
                                         ProviderAdapterBackedLLMProvider,
                                         StreamChunk)
from agent_forge.core.providers import (ChatChunk, ChatMessage, ChatResponse,
                                        ProviderAdapterError,
                                        ProviderErrorCategory,
                                        ProviderHealthResult, ProviderType,
                                        TokenUsage)


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


class TestLLMProviderBoundary:
    def test_legacy_provider_classes_are_not_exposed(self):
        assert not hasattr(llm_client_module, "KimiProvider")
        assert not hasattr(llm_client_module, "DeepSeekProvider")
        assert "KimiProvider" not in core_exports.__all__
        assert "DeepSeekProvider" not in core_exports.__all__


class FakeProviderAdapter:
    def __init__(self):
        self.chat_requests = []
        self.stream_requests = []
        self.chat_error = None

    async def chat(self, request):
        self.chat_requests.append(request)
        if self.chat_error:
            raise self.chat_error
        return ChatResponse(
            content="adapter response",
            finish_reason="stop",
            usage=TokenUsage(
                prompt_tokens=2,
                completion_tokens=3,
                total_tokens=5,
            ),
        )

    def stream(self, request):
        self.stream_requests.append(request)
        return self._stream_chunks()

    async def _stream_chunks(self):
        yield ChatChunk(content_delta="hel")
        yield ChatChunk(content_delta="lo", finish_reason="stop")

    async def list_models(self):
        return []

    async def test_connection(self, model_id=None):
        return ProviderHealthResult(status="ok", model_tested=model_id)

    def normalize_error(self, error):
        return ProviderAdapterError(
            category=ProviderErrorCategory.UNKNOWN_ERROR,
            message=str(error),
            provider_type=ProviderType.MOONSHOT,
        )


class FakeProviderAdapterResolver:
    def __init__(self):
        self.calls = []

    def resolve(self, provider_config, *, api_key, http_client=None):
        self.calls.append(
            {
                "provider_config": provider_config,
                "api_key": api_key,
                "http_client": http_client,
            }
        )
        return FakeProviderAdapter()


class TestProviderAdapterBackedLLMProvider:
    @pytest.fixture
    def adapter(self):
        return FakeProviderAdapter()

    @pytest.fixture
    def provider(self, adapter):
        return ProviderAdapterBackedLLMProvider(
            adapter=adapter,
            provider_type=ProviderType.MOONSHOT,
            default_model="moonshot-v1-8k",
        )

    @pytest.mark.asyncio
    async def test_chat_maps_legacy_request_to_provider_adapter(
        self, provider, adapter
    ):
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "Be brief"},
                {"role": "user", "content": "Ping"},
            ],
            temperature=0.2,
            max_tokens=128,
            response_format={"type": "json_object"},
        )

        assert isinstance(response, LLMResponse)
        assert response.content == "adapter response"
        assert response.model == "moonshot-v1-8k"
        assert response.usage == {
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
        }
        request = adapter.chat_requests[0]
        assert request.messages == [
            ChatMessage(role="system", content="Be brief"),
            ChatMessage(role="user", content="Ping"),
        ]
        assert request.model == "moonshot-v1-8k"
        assert request.temperature == 0.2
        assert request.max_tokens == 128
        assert request.response_format == {"type": "json_object"}
        assert request.stream is False

    @pytest.mark.asyncio
    async def test_chat_stream_maps_adapter_chunks_to_legacy_chunks(
        self, provider, adapter
    ):
        chunks = [
            chunk
            async for chunk in provider.chat_stream(
                messages=[{"role": "user", "content": "Ping"}],
                model="moonshot-v1-32k",
                temperature=0.3,
            )
        ]

        assert chunks == [
            StreamChunk(content="hel", is_finished=False),
            StreamChunk(content="lo", is_finished=True),
        ]
        request = adapter.stream_requests[0]
        assert request.model == "moonshot-v1-32k"
        assert request.temperature == 0.3
        assert request.stream is True

    @pytest.mark.asyncio
    async def test_chat_wraps_normalized_adapter_errors(self, provider, adapter):
        adapter.chat_error = ProviderAdapterError(
            category=ProviderErrorCategory.RATE_LIMITED,
            message="Rate limit reached",
            provider_type=ProviderType.MOONSHOT,
            retryable=True,
        )

        with pytest.raises(LLMException) as exc_info:
            await provider.chat(messages=[{"role": "user", "content": "Ping"}])

        assert "provider_rate_limited" in str(exc_info.value)
        assert "Rate limit reached" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_invokes_configured_close_handler(self, adapter):
        close_handler = AsyncMock()
        provider = ProviderAdapterBackedLLMProvider(
            adapter=adapter,
            provider_type=ProviderType.MOONSHOT,
            default_model="moonshot-v1-8k",
            close_handler=close_handler,
        )

        await provider.close()

        close_handler.assert_awaited_once()


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

    def test_default_providers_use_provider_adapter_resolver(self, monkeypatch):
        monkeypatch.setattr(
            "agent_forge.core.llm_client.settings.KIMI_API_KEY", "sk-kimi"
        )
        monkeypatch.setattr(
            "agent_forge.core.llm_client.settings.DEEPSEEK_API_KEY", "sk-deepseek"
        )
        monkeypatch.setattr(
            "agent_forge.core.llm_client.settings.KIMI_BASE_URL",
            "https://api.moonshot.cn",
        )
        monkeypatch.setattr(
            "agent_forge.core.llm_client.settings.DEEPSEEK_BASE_URL",
            "https://api.deepseek.com",
        )
        resolver = FakeProviderAdapterResolver()

        router = LLMRouter(provider_adapter_resolver=resolver)

        assert isinstance(router.providers["kimi"], ProviderAdapterBackedLLMProvider)
        assert isinstance(
            router.providers["deepseek"], ProviderAdapterBackedLLMProvider
        )
        calls_by_type = {
            call["provider_config"].provider_type: call for call in resolver.calls
        }
        kimi_call = calls_by_type[ProviderType.MOONSHOT]
        deepseek_call = calls_by_type[ProviderType.DEEPSEEK]
        assert kimi_call["api_key"] == "sk-kimi"
        assert kimi_call["provider_config"].base_url == "https://api.moonshot.cn/v1"
        assert kimi_call["provider_config"].default_model == "moonshot-v1-8k"
        assert deepseek_call["api_key"] == "sk-deepseek"
        assert deepseek_call["provider_config"].base_url == "https://api.deepseek.com"
        assert deepseek_call["provider_config"].default_model == "deepseek-chat"

    @pytest.mark.asyncio
    async def test_refresh_from_manager_uses_provider_adapter_resolver(
        self, monkeypatch
    ):
        class FakeApiKeyManager:
            def __init__(self):
                self.cache_cleared = False

            async def get_all_keys(self, db, user_id):
                return {
                    "kimi": "sk-kimi-from-db",
                    "deepseek": "sk-deepseek-from-db",
                    "unknown": "sk-unknown",
                }

            def clear_cache(self):
                self.cache_cleared = True

        monkeypatch.setattr(
            "agent_forge.core.llm_client.settings.KIMI_API_KEY", None
        )
        monkeypatch.setattr(
            "agent_forge.core.llm_client.settings.DEEPSEEK_API_KEY", None
        )
        resolver = FakeProviderAdapterResolver()
        api_key_manager = FakeApiKeyManager()
        router = LLMRouter(
            api_key_manager=api_key_manager,
            provider_adapter_resolver=resolver,
        )

        await router.refresh_from_manager(user_id="user-1", db=object())

        assert isinstance(router.providers["kimi"], ProviderAdapterBackedLLMProvider)
        assert isinstance(
            router.providers["deepseek"], ProviderAdapterBackedLLMProvider
        )
        assert "unknown" not in router.providers
        assert [call["api_key"] for call in resolver.calls] == [
            "sk-kimi-from-db",
            "sk-deepseek-from-db",
        ]
        assert api_key_manager.cache_cleared

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

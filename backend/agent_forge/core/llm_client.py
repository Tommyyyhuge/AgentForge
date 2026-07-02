"""
AgentForge LLM 客户端模块

支持多提供商（Kimi、DeepSeek 等）的 LLM 客户端，
包含智能路由功能，根据任务复杂度自动选择合适的模型。
"""
import time
from abc import ABC, abstractmethod
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

import httpx

from agent_forge.config.settings import settings
from agent_forge.core.error_handler import LLMException
from agent_forge.core.providers import (
    ChatMessage,
    ChatRequest,
    ProviderAdapter,
    ProviderAdapterError,
    ProviderAdapterResolver,
    ProviderErrorCategory,
    ProviderRegistry,
    ProviderType,
    TokenUsage,
)
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

_provider_metrics_task_id: ContextVar[Optional[str]] = ContextVar(
    "provider_metrics_task_id",
    default=None,
)


def bind_provider_metrics_task(task_id: str):
    return _provider_metrics_task_id.set(task_id)


def reset_provider_metrics_task(token) -> None:
    _provider_metrics_task_id.reset(token)


@dataclass
class LLMResponse:
    """LLM 响应数据类"""

    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0


@dataclass
class StreamChunk:
    """流式响应块数据类"""

    content: str
    is_finished: bool = False


@dataclass(frozen=True)
class _LLMProviderRegistration:
    provider_type: ProviderType
    api_key_setting: str
    base_url_setting: str
    append_v1_to_base_url: bool = False


_DEFAULT_PROVIDER_REGISTRATIONS: Dict[str, _LLMProviderRegistration] = {
    "kimi": _LLMProviderRegistration(
        provider_type=ProviderType.MOONSHOT,
        api_key_setting="KIMI_API_KEY",
        base_url_setting="KIMI_BASE_URL",
        append_v1_to_base_url=True,
    ),
    "deepseek": _LLMProviderRegistration(
        provider_type=ProviderType.DEEPSEEK,
        api_key_setting="DEEPSEEK_API_KEY",
        base_url_setting="DEEPSEEK_BASE_URL",
    ),
}


class BaseLLMProvider(ABC):
    """LLM 提供商基类

    所有 LLM 提供商必须继承此类并实现 chat 方法。
    """

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        # 修复：设置连接池限制，防止高并发时耗尽连接
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
            limits=limits,
        )

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """发送聊天请求

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model: 模型名称
            temperature: 温度参数
            **kwargs: 额外参数

        Returns:
            LLMResponse 实例
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """发送流式聊天请求

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            **kwargs: 额外参数

        Yields:
            StreamChunk 实例
        """
        pass

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


class ProviderAdapterBackedLLMProvider(BaseLLMProvider):
    """Compatibility bridge from the legacy LLM provider API to ProviderAdapter."""

    def __init__(
        self,
        *,
        adapter: ProviderAdapter,
        provider_type: ProviderType,
        default_model: Optional[str] = None,
        close_handler: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        self.adapter = adapter
        self.provider_type = provider_type
        self.default_model = default_model
        self._close_handler = close_handler

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        start_time = time.time()
        request = self._build_request(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=False,
            kwargs=kwargs,
        )
        try:
            response = await self.adapter.chat(request)
        except ProviderAdapterError as exc:
            raise self._to_llm_exception(exc) from exc
        except Exception as exc:
            raise self._to_llm_exception(self.adapter.normalize_error(exc)) from exc

        latency = int((time.time() - start_time) * 1000)
        return LLMResponse(
            content=response.content,
            model=request.model or "",
            usage=self._usage_to_dict(response.usage),
            latency_ms=latency,
        )

    async def chat_stream(  # type: ignore[override]
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        request = self._build_request(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True,
            kwargs=kwargs,
        )
        try:
            async for chunk in self.adapter.stream(request):
                yield StreamChunk(
                    content=chunk.content_delta,
                    is_finished=chunk.finish_reason is not None,
                )
        except ProviderAdapterError as exc:
            raise self._to_llm_exception(exc) from exc
        except Exception as exc:
            raise self._to_llm_exception(self.adapter.normalize_error(exc)) from exc

    async def close(self):
        if self._close_handler:
            await self._close_handler()

    def _build_request(
        self,
        *,
        messages: List[Dict[str, str]],
        model: Optional[str],
        temperature: float,
        stream: bool,
        kwargs: Dict[str, Any],
    ) -> ChatRequest:
        remaining_kwargs = dict(kwargs)
        metadata: Dict[str, Any] = {}
        max_tokens = remaining_kwargs.pop("max_tokens", None)
        tools = remaining_kwargs.pop("tools", None)
        tool_choice = remaining_kwargs.pop("tool_choice", None)
        response_format = remaining_kwargs.pop("response_format", None)
        if remaining_kwargs:
            metadata["legacy_kwargs"] = remaining_kwargs

        return ChatRequest(
            messages=[
                ChatMessage(role=message["role"], content=message["content"])
                for message in messages
            ],
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            stream=stream,
            metadata=metadata,
        )

    @staticmethod
    def _usage_to_dict(usage: Optional[TokenUsage]) -> Dict[str, int]:
        if usage is None:
            return {}
        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

    @staticmethod
    def _to_llm_exception(error: ProviderAdapterError) -> LLMException:
        return LLMException(f"{error.category.value}: {error.message}")


class LLMRouter:
    """LLM 路由器

    管理多个 LLM 提供商，根据任务特征自动选择最佳模型。
    支持故障转移和负载均衡。
    支持从 APIKeyManager 动态加载加密存储的 API Key。
    """

    # 复杂度 -> 推荐模型映射
    COMPLEXITY_MODELS = {
        "simple": ["moonshot-v1-8k", "deepseek-chat"],
        "medium": ["moonshot-v1-32k", "deepseek-chat"],
        "complex": ["moonshot-v1-128k", "deepseek-coder"],
    }

    def __init__(
        self,
        api_key_manager=None,
        provider_adapter_resolver: Optional[ProviderAdapterResolver] = None,
        provider_registry: Optional[ProviderRegistry] = None,
    ):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.fallback_chain: List[str] = []
        self._api_key_manager = api_key_manager  # 可选，从加密存储获取 Key
        self._provider_registry = provider_registry or ProviderRegistry()
        self._provider_adapter_resolver = (
            provider_adapter_resolver
            or ProviderAdapterResolver(registry=self._provider_registry)
        )
        self._setup_default_providers()

    async def refresh_from_manager(self, user_id: Optional[str] = None, db=None):
        """从 APIKeyManager 刷新提供商（使用加密存储的 Key）

        如果 APIKeyManager 可用且数据库中有 Key，则用加密存储的 Key
        替换 settings 中的 Key。settings 中的 Key 作为兜底。

        Args:
            user_id: 可选，限定用户
            db: 数据库会话
        """
        if not self._api_key_manager or not db:
            return

        keys = await self._api_key_manager.get_all_keys(db, user_id)

        for provider_name, api_key in keys.items():
            registration = _DEFAULT_PROVIDER_REGISTRATIONS.get(provider_name)
            if not registration or not api_key:
                continue

            self._register_adapter_provider(
                provider_name,
                registration,
                api_key=api_key,
            )
            logger.info(f"从加密存储加载 {provider_name} API Key")

        self._api_key_manager.clear_cache()

    def _setup_default_providers(self):
        """设置默认提供商"""
        for provider_name, registration in _DEFAULT_PROVIDER_REGISTRATIONS.items():
            api_key = getattr(settings, registration.api_key_setting)
            if not api_key:
                continue
            self._register_adapter_provider(
                provider_name,
                registration,
                api_key=api_key,
            )

    def _register_adapter_provider(
        self,
        provider_name: str,
        registration: _LLMProviderRegistration,
        *,
        api_key: str,
    ) -> None:
        provider_config = self._build_provider_config(registration)
        http_client = httpx.AsyncClient(timeout=provider_config.timeout_seconds)
        adapter = self._provider_adapter_resolver.resolve(
            provider_config,
            api_key=api_key,
            http_client=http_client,
        )
        provider = ProviderAdapterBackedLLMProvider(
            adapter=adapter,
            provider_type=provider_config.provider_type,
            default_model=provider_config.default_model,
            close_handler=http_client.aclose,
        )
        self.register_provider(provider_name, provider)

    def _build_provider_config(self, registration: _LLMProviderRegistration):
        provider_config = self._provider_registry.build_config_from_preset(
            registration.provider_type
        )
        base_url = getattr(settings, registration.base_url_setting)
        if base_url:
            base_url = base_url.rstrip("/")
            if registration.append_v1_to_base_url and not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            provider_config = provider_config.model_copy(
                update={"base_url": base_url}
            )
        return self._provider_registry.validate_config(provider_config)

    def register_provider(self, name: str, provider: BaseLLMProvider):
        """注册 LLM 提供商

        Args:
            name: 提供商名称
            provider: 提供商实例
        """
        self.providers[name] = provider
        if name not in self.fallback_chain:
            self.fallback_chain.append(name)
        logger.info(f"已注册 LLM 提供商: {name}")

    def get_provider(self, name: Optional[str] = None) -> BaseLLMProvider:
        """获取提供商

        Args:
            name: 提供商名称，None 则使用第一个可用提供商

        Returns:
            BaseLLMProvider 实例

        Raises:
            LLMException: 没有可用提供商时抛出
        """
        if name and name in self.providers:
            return self.providers[name]

        if self.fallback_chain:
            return self.providers[self.fallback_chain[0]]

        raise LLMException("没有可用的 LLM 提供商，请配置 API Key")

    async def route(
        self,
        messages: List[Dict[str, str]],
        complexity: str = "medium",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """智能路由并调用 LLM

        Args:
            messages: 消息列表
            complexity: 任务复杂度 (simple/medium/complex)
            provider: 指定提供商名称
            model: 指定模型名称
            **kwargs: 额外参数

        Returns:
            LLMResponse 实例
        """
        provider_name = self._select_provider_name(provider)
        llm_provider = self.get_provider(provider_name)

        # 如果未指定模型，根据复杂度选择
        if not model and complexity in self.COMPLEXITY_MODELS:
            model = self.COMPLEXITY_MODELS[complexity][0]

        logger.info(
            f"LLM 路由: provider={provider or 'auto'}, "
            f"model={model or 'default'}, complexity={complexity}"
        )

        start_time = time.time()
        try:
            response = await llm_provider.chat(messages=messages, model=model, **kwargs)
        except Exception as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            await self._record_provider_metric_for_active_task(
                {
                    "provider": provider_name,
                    "model": model or "default",
                    "latencyMs": latency_ms,
                    "status": "failed",
                    "errorCategory": self._provider_error_category(exc),
                }
            )
            raise

        usage = response.usage or {}
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get(
            "output_tokens",
            usage.get("completion_tokens", 0),
        )
        await self._record_provider_metric_for_active_task(
            {
                "provider": provider_name,
                "model": response.model or model or "default",
                "latencyMs": response.latency_ms
                or int((time.time() - start_time) * 1000),
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "totalTokens": usage.get(
                    "total_tokens",
                    input_tokens + output_tokens,
                ),
                "status": "success",
            }
        )
        return response

    async def route_stream(  # type: ignore[override]
        self,
        messages: List[Dict[str, str]],
        complexity: str = "medium",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式智能路由

        Args:
            messages: 消息列表
            complexity: 任务复杂度
            provider: 指定提供商名称
            model: 指定模型名称
            **kwargs: 额外参数

        Yields:
            StreamChunk 实例
        """
        llm_provider = self.get_provider(provider)

        if not model and complexity in self.COMPLEXITY_MODELS:
            model = self.COMPLEXITY_MODELS[complexity][0]

        async for chunk in llm_provider.chat_stream(  # type: ignore[attr-defined]
            messages=messages, model=model, **kwargs
        ):
            yield chunk

    async def close_all(self):
        """关闭所有提供商连接"""
        for name, provider in self.providers.items():
            await provider.close()
            logger.info(f"已关闭 LLM 提供商连接: {name}")

    def _select_provider_name(self, provider: Optional[str]) -> str:
        if provider and provider in self.providers:
            return provider
        if self.fallback_chain:
            return self.fallback_chain[0]
        return provider or "unknown"

    async def _record_provider_metric_for_active_task(
        self,
        metric: Dict[str, Any],
    ) -> None:
        task_id = _provider_metrics_task_id.get()
        if not task_id:
            return

        try:
            from agent_forge.core.metrics_service import MetricsService
            from agent_forge.database.connection import async_session

            async with async_session() as db:
                await MetricsService.append_provider_metric(db, task_id, metric)
        except Exception as exc:
            logger.warning("Provider metric recording failed: %s", exc)

    @staticmethod
    def _provider_error_category(exc: Exception) -> str:
        message = str(exc)
        for category in ProviderErrorCategory:
            if message.startswith(category.value):
                return category.value
        return ProviderErrorCategory.UNKNOWN_ERROR.value

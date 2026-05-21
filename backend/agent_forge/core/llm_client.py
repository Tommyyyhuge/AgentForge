"""
AgentForge LLM 客户端模块

支持多提供商（Kimi、DeepSeek 等）的 LLM 客户端，
包含智能路由功能，根据任务复杂度自动选择合适的模型。
"""
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from agent_forge.config.settings import settings
from agent_forge.core.error_handler import LLMException
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


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


class KimiProvider(BaseLLMProvider):
    """Kimi (Moonshot) LLM 提供商"""

    DEFAULT_MODEL = "moonshot-v1-8k"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Kimi 聊天实现"""
        start_time = time.time()
        model = model or self.DEFAULT_MODEL

        try:
            response = await self.client.post(
                "/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    **kwargs,
                },
            )
            response.raise_for_status()
            data = response.json()

            latency = int((time.time() - start_time) * 1000)

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                usage=data.get("usage", {}),
                latency_ms=latency,
            )
        except httpx.HTTPStatusError as e:
            raise LLMException(
                f"Kimi API 请求失败: {e.response.status_code} - {e.response.text}"
            )
        except (httpx.RequestError, json.JSONDecodeError, KeyError, IndexError) as e:
            raise LLMException(f"Kimi API 调用异常: {str(e)}")

    async def chat_stream(  # type: ignore[override]
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Kimi 流式聊天实现"""
        model = model or self.DEFAULT_MODEL

        try:
            async with self.client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                    **kwargs,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield StreamChunk(content="", is_finished=True)
                            break
                        # 解析 JSON 数据
                        import json

                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            if "content" in delta:
                                yield StreamChunk(content=delta["content"])
                        except (json.JSONDecodeError, KeyError):
                            continue
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise LLMException(f"Kimi 流式 API 调用异常: {str(e)}")


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek LLM 提供商"""

    DEFAULT_MODEL = "deepseek-chat"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """DeepSeek 聊天实现"""
        start_time = time.time()
        model = model or self.DEFAULT_MODEL

        try:
            response = await self.client.post(
                "/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    **kwargs,
                },
            )
            response.raise_for_status()
            data = response.json()

            latency = int((time.time() - start_time) * 1000)

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                usage=data.get("usage", {}),
                latency_ms=latency,
            )
        except httpx.HTTPStatusError as e:
            raise LLMException(
                f"DeepSeek API 请求失败: {e.response.status_code} - {e.response.text}"
            )
        except (httpx.RequestError, json.JSONDecodeError, KeyError, IndexError) as e:
            raise LLMException(f"DeepSeek API 调用异常: {str(e)}")

    async def chat_stream(  # type: ignore[override]
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """DeepSeek 流式聊天实现"""
        model = model or self.DEFAULT_MODEL

        try:
            async with self.client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                    **kwargs,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield StreamChunk(content="", is_finished=True)
                            break
                        import json

                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            if "content" in delta:
                                yield StreamChunk(content=delta["content"])
                        except (json.JSONDecodeError, KeyError):
                            continue
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise LLMException(f"DeepSeek 流式 API 调用异常: {str(e)}")


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

    def __init__(self, api_key_manager=None):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.fallback_chain: List[str] = []
        self._api_key_manager = api_key_manager  # 可选，从加密存储获取 Key
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

        from agent_forge.core.api_key_manager import APIKeyManager
        keys = await self._api_key_manager.get_all_keys(db, user_id)

        for provider_name, api_key in keys.items():
            if provider_name == "kimi" and api_key:
                kimi = KimiProvider(
                    api_key=api_key, base_url=settings.KIMI_BASE_URL
                )
                self.register_provider("kimi", kimi)
                logger.info("从加密存储加载 Kimi API Key")

            elif provider_name == "deepseek" and api_key:
                deepseek = DeepSeekProvider(
                    api_key=api_key, base_url=settings.DEEPSEEK_BASE_URL
                )
                self.register_provider("deepseek", deepseek)
                logger.info("从加密存储加载 DeepSeek API Key")

        self._api_key_manager.clear_cache()

    def _setup_default_providers(self):
        """设置默认提供商"""
        # Kimi
        if settings.KIMI_API_KEY:
            kimi = KimiProvider(
                api_key=settings.KIMI_API_KEY, base_url=settings.KIMI_BASE_URL
            )
            self.register_provider("kimi", kimi)

        # DeepSeek
        if settings.DEEPSEEK_API_KEY:
            deepseek = DeepSeekProvider(
                api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL
            )
            self.register_provider("deepseek", deepseek)

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
        llm_provider = self.get_provider(provider)

        # 如果未指定模型，根据复杂度选择
        if not model and complexity in self.COMPLEXITY_MODELS:
            model = self.COMPLEXITY_MODELS[complexity][0]

        logger.info(
            f"LLM 路由: provider={provider or 'auto'}, "
            f"model={model or 'default'}, complexity={complexity}"
        )

        return await llm_provider.chat(messages=messages, model=model, **kwargs)

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

"""Shared OpenAI-compatible Provider transport."""

import json
import time
from typing import Any, AsyncIterator

import httpx

from agent_forge.core.providers.adapter import (
    ChatChunk,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ModelInfo,
    ProviderAdapterError,
    ProviderErrorCategory,
    ProviderHealthResult,
    TokenUsage,
)
from agent_forge.core.providers.models import ProviderConfig, ProviderType


class OpenAICompatibleAdapterBase:
    """Shared OpenAI-compatible chat completion transport."""

    allowed_provider_types: frozenset[ProviderType] = frozenset()
    adapter_label = "OpenAI-compatible adapter"

    def __init__(
        self,
        *,
        provider_config: ProviderConfig,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if (
            self.allowed_provider_types
            and provider_config.provider_type not in self.allowed_provider_types
        ):
            allowed_types = ", ".join(
                sorted(provider_type.value for provider_type in self.allowed_provider_types)
            )
            raise ValueError(f"{self.adapter_label} requires one of: {allowed_types}.")
        if not provider_config.base_url:
            raise ValueError(f"{self.adapter_label} requires a base URL.")
        self._provider_config = provider_config
        self._api_key = api_key
        self._http_client = http_client or httpx.AsyncClient(
            timeout=provider_config.timeout_seconds
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a non-streaming OpenAI-compatible chat completion request."""
        payload = self._build_chat_payload(request, stream=False)
        try:
            response = await self._http_client.post(
                self._endpoint("/chat/completions"),
                headers=self._headers(),
                json=payload,
            )
            self._raise_for_status(response)
            data = response.json()
            choice = self._first_choice(data)
            message = choice.get("message") or {}
            return ChatResponse(
                content=str(message.get("content") or ""),
                finish_reason=choice.get("finish_reason"),
                tool_calls=message.get("tool_calls"),
                usage=self._parse_usage(data),
                raw_provider_response=data,
            )
        except ProviderAdapterError:
            raise
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream OpenAI-compatible chat completion chunks."""
        if not self._provider_config.streaming_enabled:
            raise ProviderAdapterError(
                category=ProviderErrorCategory.UNSUPPORTED_FEATURE,
                message="Provider streaming is disabled.",
                provider_type=self._provider_config.provider_type,
                provider_id=self._provider_config.id,
                model_id=request.model or self._provider_config.default_model,
                retryable=False,
                details={"capability": "streaming"},
            )

        payload = self._build_chat_payload(request, stream=True)
        try:
            async with self._http_client.stream(
                "POST",
                self._endpoint("/chat/completions"),
                headers=self._headers(),
                json=payload,
            ) as response:
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    chunk = self._parse_stream_line(line)
                    if chunk is not None:
                        yield chunk
        except ProviderAdapterError:
            raise
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def list_models(self) -> list[ModelInfo]:
        """List models from an OpenAI-compatible endpoint."""
        try:
            response = await self._http_client.get(
                self._endpoint("/models"),
                headers=self._headers(),
            )
            self._raise_for_status(response)
            data = response.json()
            models = data.get("data") if isinstance(data, dict) else []
            if not isinstance(models, list):
                return []
            return [
                ModelInfo(
                    id=str(model.get("id")),
                    display_name=str(model.get("id")),
                    raw_provider_model=model,
                )
                for model in models
                if isinstance(model, dict) and model.get("id")
            ]
        except ProviderAdapterError:
            raise
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def test_connection(
        self,
        model_id: str | None = None,
    ) -> ProviderHealthResult:
        """Run a user-safe connection test against the chat endpoint."""
        tested_model = model_id or self._provider_config.default_model
        started_at = time.perf_counter()
        try:
            await self.chat(
                ChatRequest(
                    model=tested_model,
                    messages=[
                        ChatMessage(role="user", content="ping"),
                    ],
                    max_tokens=1,
                )
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            return ProviderHealthResult(
                status="healthy",
                latency_ms=latency_ms,
                model_tested=tested_model,
            )
        except ProviderAdapterError as exc:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            return ProviderHealthResult(
                status="unhealthy",
                latency_ms=latency_ms,
                error_code=exc.category.value,
                error_message=exc.message,
                model_tested=tested_model,
            )

    def normalize_error(self, error: Exception) -> ProviderAdapterError:
        """Normalize transport and Provider errors without leaking secrets."""
        if isinstance(error, ProviderAdapterError):
            return error
        if isinstance(error, httpx.TimeoutException):
            return self._adapter_error(
                ProviderErrorCategory.TIMEOUT,
                "Provider request timed out.",
                retryable=True,
            )
        if isinstance(error, httpx.RequestError):
            return self._adapter_error(
                ProviderErrorCategory.NETWORK_ERROR,
                "Provider network request failed.",
                retryable=True,
                details={"error_type": type(error).__name__},
            )
        return self._adapter_error(
            ProviderErrorCategory.UNKNOWN_ERROR,
            "Provider request failed.",
            retryable=False,
            details={"error_type": type(error).__name__},
        )

    def _build_chat_payload(
        self,
        request: ChatRequest,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        model = request.model or self._provider_config.default_model
        if not model:
            raise ProviderAdapterError(
                category=ProviderErrorCategory.INVALID_REQUEST,
                message="Provider requires a model.",
                provider_type=self._provider_config.provider_type,
                provider_id=self._provider_config.id,
            )

        payload: dict[str, Any] = {
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "model": model,
            "stream": stream,
        }
        optional_fields = {
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "tools": request.tools,
            "tool_choice": request.tool_choice,
            "response_format": request.response_format,
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value
        return payload

    def _endpoint(self, path: str) -> str:
        return f"{(self._provider_config.base_url or '').rstrip('/')}{path}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        raise self._error_from_response(response)

    def _error_from_response(self, response: httpx.Response) -> ProviderAdapterError:
        category = self._category_for_status(response.status_code)
        error_message = self._safe_error_message(response, category)
        return self._adapter_error(
            category,
            error_message,
            retryable=category
            in {
                ProviderErrorCategory.RATE_LIMITED,
                ProviderErrorCategory.TIMEOUT,
                ProviderErrorCategory.NETWORK_ERROR,
                ProviderErrorCategory.SERVER_ERROR,
            },
            details={
                "status_code": response.status_code,
                "provider_error": self._safe_provider_error(response),
            },
        )

    def _adapter_error(
        self,
        category: ProviderErrorCategory,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> ProviderAdapterError:
        return ProviderAdapterError(
            category=category,
            message=self._redact_secret_text(message),
            provider_type=self._provider_config.provider_type,
            provider_id=self._provider_config.id,
            retryable=retryable,
            details=self._redact_secret_value(details or {}),
        )

    def _redact_secret_text(self, value: str) -> str:
        if self._api_key:
            return value.replace(self._api_key, "[REDACTED]")
        return value

    def _redact_secret_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redact_secret_text(value)
        if isinstance(value, dict):
            return {
                key: self._redact_secret_value(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._redact_secret_value(item) for item in value]
        return value

    @staticmethod
    def _category_for_status(status_code: int) -> ProviderErrorCategory:
        if status_code in {401, 403}:
            return ProviderErrorCategory.AUTH_FAILED
        if status_code == 404:
            return ProviderErrorCategory.MODEL_NOT_FOUND
        if status_code == 408:
            return ProviderErrorCategory.TIMEOUT
        if status_code == 429:
            return ProviderErrorCategory.RATE_LIMITED
        if status_code == 402:
            return ProviderErrorCategory.QUOTA_EXCEEDED
        if status_code >= 500:
            return ProviderErrorCategory.SERVER_ERROR
        if status_code >= 400:
            return ProviderErrorCategory.INVALID_REQUEST
        return ProviderErrorCategory.UNKNOWN_ERROR

    @staticmethod
    def _safe_provider_error(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        error = data.get("error")
        if not isinstance(error, dict):
            return {}
        return {
            key: value
            for key, value in error.items()
            if key in {"code", "message", "type", "param"}
        }

    def _safe_error_message(
        self,
        response: httpx.Response,
        category: ProviderErrorCategory,
    ) -> str:
        provider_error = self._safe_provider_error(response)
        message = provider_error.get("message")
        if isinstance(message, str) and message:
            return message
        defaults = {
            ProviderErrorCategory.AUTH_FAILED: "Provider authentication failed.",
            ProviderErrorCategory.RATE_LIMITED: "Provider rate limit exceeded.",
            ProviderErrorCategory.MODEL_NOT_FOUND: "Provider model was not found.",
            ProviderErrorCategory.TIMEOUT: "Provider request timed out.",
            ProviderErrorCategory.QUOTA_EXCEEDED: "Provider quota was exceeded.",
            ProviderErrorCategory.SERVER_ERROR: "Provider server error.",
            ProviderErrorCategory.INVALID_REQUEST: "Provider rejected the request.",
        }
        return defaults.get(category, "Provider request failed.")

    @staticmethod
    def _first_choice(data: dict[str, Any]) -> dict[str, Any]:
        choices = data.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            return choices[0]
        return {}

    @staticmethod
    def _parse_usage(data: dict[str, Any]) -> TokenUsage | None:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        return TokenUsage(
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
        )

    def _parse_stream_line(self, line: str) -> ChatChunk | None:
        stripped = line.strip()
        if not stripped or stripped.startswith(":") or not stripped.startswith("data:"):
            return None
        payload = stripped.removeprefix("data:").strip()
        if payload == "[DONE]":
            return None
        data = json.loads(payload)
        if not isinstance(data, dict):
            return None
        choice = self._first_choice(data)
        delta = choice.get("delta") if isinstance(choice, dict) else {}
        if not isinstance(delta, dict):
            delta = {}
        usage = self._parse_usage(data)
        chunk = ChatChunk(
            content_delta=str(delta.get("content") or ""),
            finish_reason=choice.get("finish_reason"),
            tool_calls_delta=delta.get("tool_calls"),
            usage=usage,
            raw_provider_chunk=data,
        )
        if (
            chunk.content_delta
            or chunk.finish_reason
            or chunk.tool_calls_delta
            or chunk.usage
        ):
            return chunk
        return None

"""Official Provider adapters."""

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
from agent_forge.core.providers.openai_compatible import OpenAICompatibleAdapterBase

ANTHROPIC_API_VERSION = "2023-06-01"

OPENAI_COMPATIBLE_OFFICIAL_PROVIDER_TYPES = frozenset(
    {
        ProviderType.OPENAI,
        ProviderType.DEEPSEEK,
        ProviderType.MOONSHOT,
    }
)


class OpenAICompatibleOfficialAdapter(OpenAICompatibleAdapterBase):
    """Adapter for official APIs with OpenAI-compatible chat semantics."""

    allowed_provider_types = OPENAI_COMPATIBLE_OFFICIAL_PROVIDER_TYPES
    adapter_label = "Official OpenAI-compatible adapter"


class DashScopeOfficialAdapter(OpenAICompatibleAdapterBase):
    """Adapter for DashScope's official OpenAI-compatible mode."""

    allowed_provider_types = frozenset({ProviderType.DASHSCOPE})
    adapter_label = "DashScope adapter"

    def _build_chat_payload(
        self,
        request: ChatRequest,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        payload = super()._build_chat_payload(request, stream=stream)
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    def _endpoint(self, path: str) -> str:
        base_url = (self._provider_config.base_url or "").rstrip("/")
        compatible_base = (
            base_url
            if base_url.endswith("/compatible-mode/v1")
            else f"{base_url}/compatible-mode/v1"
        )
        return f"{compatible_base}{path}"


class AnthropicOfficialAdapter:
    """Adapter for Anthropic's official Messages API."""

    def __init__(
        self,
        *,
        provider_config: ProviderConfig,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if provider_config.provider_type != ProviderType.ANTHROPIC:
            raise ValueError("Anthropic adapter requires an anthropic config.")
        if not provider_config.base_url:
            raise ValueError("Anthropic adapter requires a base URL.")
        self._provider_config = provider_config
        self._api_key = api_key
        self._http_client = http_client or httpx.AsyncClient(
            timeout=provider_config.timeout_seconds
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a non-streaming Anthropic Messages request."""
        payload = self._build_chat_payload(request, stream=False)
        try:
            response = await self._http_client.post(
                self._endpoint("/v1/messages"),
                headers=self._headers(),
                json=payload,
            )
            self._raise_for_status(response)
            data = response.json()
            return ChatResponse(
                content=self._parse_content(data),
                finish_reason=self._parse_finish_reason(data),
                usage=self._parse_usage(data),
                raw_provider_response=data,
            )
        except ProviderAdapterError:
            raise
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream Anthropic Messages text deltas."""
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
                self._endpoint("/v1/messages"),
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
        """Anthropic model listing is not part of this AF-007 slice."""
        raise ProviderAdapterError(
            category=ProviderErrorCategory.UNSUPPORTED_FEATURE,
            message="Anthropic model listing is not enabled.",
            provider_type=self._provider_config.provider_type,
            provider_id=self._provider_config.id,
            retryable=False,
            details={"capability": "model_listing"},
        )

    async def test_connection(
        self,
        model_id: str | None = None,
    ) -> ProviderHealthResult:
        """Run a user-safe connection test against Anthropic Messages."""
        tested_model = model_id or self._provider_config.default_model
        started_at = time.perf_counter()
        try:
            await self.chat(
                ChatRequest(
                    model=tested_model,
                    messages=[ChatMessage(role="user", content="ping")],
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
        """Normalize Anthropic transport and Provider errors."""
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
        self._reject_unsupported_fields(request)
        model = request.model or self._provider_config.default_model
        if not model:
            raise self._adapter_error(
                ProviderErrorCategory.INVALID_REQUEST,
                "Provider requires a model.",
            )

        system_messages: list[str] = []
        messages: list[dict[str, str]] = []
        for message in request.messages:
            if message.role == "system":
                system_messages.append(message.content)
                continue
            if message.role not in {"user", "assistant"}:
                raise self._adapter_error(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Anthropic messages support user and assistant roles.",
                    details={"role": message.role},
                )
            messages.append({"role": message.role, "content": message.content})

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": (
                request.max_tokens if request.max_tokens is not None else 1024
            ),
            "messages": messages,
        }
        if system_messages:
            payload["system"] = "\n\n".join(system_messages)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if stream:
            payload["stream"] = True
        return payload

    def _reject_unsupported_fields(self, request: ChatRequest) -> None:
        if request.response_format is not None:
            raise self._adapter_error(
                ProviderErrorCategory.UNSUPPORTED_FEATURE,
                "Anthropic adapter does not support JSON mode mapping yet.",
                details={"capability": "json_mode"},
            )
        if request.tools is not None or request.tool_choice is not None:
            raise self._adapter_error(
                ProviderErrorCategory.UNSUPPORTED_FEATURE,
                "Anthropic adapter does not support tool calling mapping yet.",
                details={"capability": "tool_calling"},
            )

    def _endpoint(self, path: str) -> str:
        return f"{(self._provider_config.base_url or '').rstrip('/')}{path}"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": ANTHROPIC_API_VERSION,
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        raise self._error_from_response(response)

    def _error_from_response(self, response: httpx.Response) -> ProviderAdapterError:
        category = self._category_for_status(response.status_code)
        return self._adapter_error(
            category,
            self._safe_error_message(response, category),
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
    def _parse_content(data: dict[str, Any]) -> str:
        content = data.get("content")
        if not isinstance(content, list):
            return ""
        text_blocks = [
            str(block.get("text"))
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
            and block.get("text") is not None
        ]
        return "".join(text_blocks)

    @staticmethod
    def _parse_finish_reason(data: dict[str, Any]) -> str | None:
        stop_reason = data.get("stop_reason")
        if isinstance(stop_reason, str):
            return stop_reason
        return None

    @staticmethod
    def _parse_usage(data: dict[str, Any]) -> TokenUsage | None:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        return TokenUsage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

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
            if key in {"type", "message"}
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

    def _parse_stream_line(self, line: str) -> ChatChunk | None:
        stripped = line.strip()
        if not stripped or stripped.startswith(":") or not stripped.startswith("data:"):
            return None
        payload = stripped.removeprefix("data:").strip()
        data = json.loads(payload)
        if not isinstance(data, dict):
            return None

        event_type = data.get("type")
        if event_type == "content_block_delta":
            delta = data.get("delta")
            if not isinstance(delta, dict):
                return None
            text = delta.get("text")
            if isinstance(text, str):
                return ChatChunk(content_delta=text, raw_provider_chunk=data)
            return None
        if event_type == "message_delta":
            delta = data.get("delta")
            if not isinstance(delta, dict):
                delta = {}
            return ChatChunk(
                finish_reason=self._parse_delta_finish_reason(delta),
                usage=self._parse_stream_usage(data),
                raw_provider_chunk=data,
            )
        return None

    @staticmethod
    def _parse_delta_finish_reason(delta: dict[str, Any]) -> str | None:
        stop_reason = delta.get("stop_reason")
        if isinstance(stop_reason, str):
            return stop_reason
        return None

    @staticmethod
    def _parse_stream_usage(data: dict[str, Any]) -> TokenUsage | None:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        output_tokens = int(usage.get("output_tokens") or 0)
        return TokenUsage(
            prompt_tokens=0,
            completion_tokens=output_tokens,
            total_tokens=output_tokens,
        )


class GeminiOfficialAdapter:
    """Adapter for Google's official Gemini generateContent API."""

    def __init__(
        self,
        *,
        provider_config: ProviderConfig,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if provider_config.provider_type != ProviderType.GEMINI:
            raise ValueError("Gemini adapter requires a gemini config.")
        if not provider_config.base_url:
            raise ValueError("Gemini adapter requires a base URL.")
        self._provider_config = provider_config
        self._api_key = api_key
        self._http_client = http_client or httpx.AsyncClient(
            timeout=provider_config.timeout_seconds
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a non-streaming Gemini generateContent request."""
        payload = self._build_chat_payload(request)
        model = request.model or self._provider_config.default_model
        try:
            response = await self._http_client.post(
                self._model_endpoint(model, "generateContent"),
                headers=self._headers(),
                json=payload,
            )
            self._raise_for_status(response)
            data = response.json()
            return ChatResponse(
                content=self._parse_content(data),
                finish_reason=self._parse_finish_reason(data),
                usage=self._parse_usage(data),
                raw_provider_response=data,
            )
        except ProviderAdapterError:
            raise
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream Gemini generateContent text chunks."""
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

        payload = self._build_chat_payload(request)
        model = request.model or self._provider_config.default_model
        try:
            async with self._http_client.stream(
                "POST",
                self._model_endpoint(model, "streamGenerateContent"),
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
        """Gemini model listing is not part of this AF-007 slice."""
        raise ProviderAdapterError(
            category=ProviderErrorCategory.UNSUPPORTED_FEATURE,
            message="Gemini model listing is not enabled.",
            provider_type=self._provider_config.provider_type,
            provider_id=self._provider_config.id,
            retryable=False,
            details={"capability": "model_listing"},
        )

    async def test_connection(
        self,
        model_id: str | None = None,
    ) -> ProviderHealthResult:
        """Run a user-safe connection test against Gemini generateContent."""
        tested_model = model_id or self._provider_config.default_model
        started_at = time.perf_counter()
        try:
            await self.chat(
                ChatRequest(
                    model=tested_model,
                    messages=[ChatMessage(role="user", content="ping")],
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
        """Normalize Gemini transport and Provider errors."""
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

    def _build_chat_payload(self, request: ChatRequest) -> dict[str, Any]:
        self._reject_unsupported_fields(request)
        if not request.model and not self._provider_config.default_model:
            raise self._adapter_error(
                ProviderErrorCategory.INVALID_REQUEST,
                "Provider requires a model.",
            )

        system_messages: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role == "system":
                system_messages.append(message.content)
                continue
            if message.role == "assistant":
                role = "model"
            elif message.role == "user":
                role = "user"
            else:
                raise self._adapter_error(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Gemini contents support user and assistant roles.",
                    details={"role": message.role},
                )
            contents.append(
                {
                    "role": role,
                    "parts": [{"text": message.content}],
                }
            )

        payload: dict[str, Any] = {"contents": contents}
        if system_messages:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_messages)}]
            }
        generation_config: dict[str, Any] = {}
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if generation_config:
            payload["generationConfig"] = generation_config
        return payload

    def _reject_unsupported_fields(self, request: ChatRequest) -> None:
        if request.response_format is not None:
            raise self._adapter_error(
                ProviderErrorCategory.UNSUPPORTED_FEATURE,
                "Gemini adapter does not support JSON mode mapping yet.",
                details={"capability": "json_mode"},
            )
        if request.tools is not None or request.tool_choice is not None:
            raise self._adapter_error(
                ProviderErrorCategory.UNSUPPORTED_FEATURE,
                "Gemini adapter does not support tool calling mapping yet.",
                details={"capability": "tool_calling"},
            )

    def _model_endpoint(self, model: str | None, action: str) -> str:
        if not model:
            raise self._adapter_error(
                ProviderErrorCategory.INVALID_REQUEST,
                "Provider requires a model.",
            )
        model_path = model if model.startswith("models/") else f"models/{model}"
        base_url = (self._provider_config.base_url or "").rstrip("/")
        endpoint = f"{base_url}/v1beta/{model_path}:{action}"
        if self._api_key:
            endpoint = f"{endpoint}?key={self._api_key}"
        return endpoint

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        raise self._error_from_response(response)

    def _error_from_response(self, response: httpx.Response) -> ProviderAdapterError:
        category = self._category_for_status(response.status_code)
        return self._adapter_error(
            category,
            self._safe_error_message(response, category),
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
    def _parse_content(data: dict[str, Any]) -> str:
        candidate = GeminiOfficialAdapter._first_candidate(data)
        content = candidate.get("content")
        if not isinstance(content, dict):
            return ""
        parts = content.get("parts")
        if not isinstance(parts, list):
            return ""
        return "".join(
            str(part.get("text"))
            for part in parts
            if isinstance(part, dict) and part.get("text") is not None
        )

    @staticmethod
    def _parse_finish_reason(data: dict[str, Any]) -> str | None:
        candidate = GeminiOfficialAdapter._first_candidate(data)
        finish_reason = candidate.get("finishReason")
        if isinstance(finish_reason, str):
            return finish_reason
        return None

    @staticmethod
    def _parse_usage(data: dict[str, Any]) -> TokenUsage | None:
        usage = data.get("usageMetadata")
        if not isinstance(usage, dict):
            return None
        prompt_tokens = int(usage.get("promptTokenCount") or 0)
        completion_tokens = int(usage.get("candidatesTokenCount") or 0)
        total_tokens = int(
            usage.get("totalTokenCount") or prompt_tokens + completion_tokens
        )
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    @staticmethod
    def _first_candidate(data: dict[str, Any]) -> dict[str, Any]:
        candidates = data.get("candidates")
        if (
            isinstance(candidates, list)
            and candidates
            and isinstance(candidates[0], dict)
        ):
            return candidates[0]
        return {}

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
            if key in {"code", "message", "status"}
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

    def _parse_stream_line(self, line: str) -> ChatChunk | None:
        stripped = line.strip()
        if not stripped or stripped.startswith(":"):
            return None
        if stripped.startswith("data:"):
            stripped = stripped.removeprefix("data:").strip()
        if stripped in {"[DONE]", "]", "["}:
            return None
        stripped = stripped.rstrip(",")
        data = json.loads(stripped)
        if not isinstance(data, dict):
            return None
        content_delta = self._parse_content(data)
        finish_reason = self._parse_finish_reason(data)
        usage = self._parse_usage(data)
        if content_delta or finish_reason or usage:
            return ChatChunk(
                content_delta=content_delta,
                finish_reason=finish_reason,
                usage=usage,
                raw_provider_chunk=data,
            )
        return None

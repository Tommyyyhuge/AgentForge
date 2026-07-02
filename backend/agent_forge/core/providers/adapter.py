"""Shared Provider adapter contracts and transport-safe models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Protocol

from agent_forge.core.providers.models import ProviderType


class ProviderErrorCategory(str, Enum):
    """Normalized Provider error categories."""

    AUTH_FAILED = "provider_auth_failed"
    RATE_LIMITED = "provider_rate_limited"
    MODEL_NOT_FOUND = "provider_model_not_found"
    TIMEOUT = "provider_timeout"
    NETWORK_ERROR = "provider_network_error"
    INVALID_REQUEST = "provider_invalid_request"
    UNSUPPORTED_FEATURE = "provider_unsupported_feature"
    QUOTA_EXCEEDED = "provider_quota_exceeded"
    SERVER_ERROR = "provider_server_error"
    UNKNOWN_ERROR = "provider_unknown_error"


@dataclass(frozen=True)
class ChatMessage:
    """Provider-neutral chat message."""

    role: str
    content: str


@dataclass(frozen=True)
class ChatRequest:
    """Provider-neutral chat request."""

    messages: list[ChatMessage]
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None
    response_format: dict[str, Any] | None = None
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TokenUsage:
    """Normalized token usage reported by a Provider."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ChatResponse:
    """Provider-neutral chat response."""

    content: str
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    usage: TokenUsage | None = None
    raw_provider_response: dict[str, Any] | None = None


@dataclass(frozen=True)
class ChatChunk:
    """Provider-neutral streaming chat chunk."""

    content_delta: str = ""
    finish_reason: str | None = None
    tool_calls_delta: list[dict[str, Any]] | None = None
    usage: TokenUsage | None = None
    raw_provider_chunk: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelInfo:
    """Provider-neutral model metadata."""

    id: str
    display_name: str | None = None
    raw_provider_model: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderHealthResult:
    """User-safe Provider connection test result."""

    status: str
    latency_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    model_tested: str | None = None


class ProviderAdapterError(Exception):
    """Normalized, user-safe Provider adapter error."""

    def __init__(
        self,
        *,
        category: ProviderErrorCategory,
        message: str,
        provider_type: ProviderType,
        provider_id: str | None = None,
        model_id: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.provider_type = provider_type
        self.provider_id = provider_id
        self.model_id = model_id
        self.retryable = retryable
        self.details = details or {}


class ProviderAdapter(Protocol):
    """Common Provider adapter interface used by execution code."""

    async def chat(self, request: ChatRequest) -> ChatResponse:
        ...

    def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        ...

    async def list_models(self) -> list[ModelInfo]:
        ...

    async def test_connection(self, model_id: str | None = None) -> ProviderHealthResult:
        ...

    def normalize_error(self, error: Exception) -> ProviderAdapterError:
        ...

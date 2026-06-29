"""Placeholder adapter for planned Provider integrations."""

from typing import AsyncIterator

from agent_forge.core.providers.adapter import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    ModelInfo,
    ProviderAdapterError,
    ProviderErrorCategory,
    ProviderHealthResult,
)
from agent_forge.core.providers.models import ProviderConfig, ProviderType

PLANNED_PROVIDER_TYPES = frozenset(
    {
        ProviderType.ZHIPU,
        ProviderType.QIANFAN,
        ProviderType.HUNYUAN,
        ProviderType.MINIMAX,
    }
)


class PlannedProviderAdapter:
    """Adapter placeholder that prevents execution for planned Providers."""

    def __init__(self, *, provider_config: ProviderConfig) -> None:
        if provider_config.provider_type not in PLANNED_PROVIDER_TYPES:
            raise ValueError("Planned provider adapter requires a planned Provider.")
        self._provider_config = provider_config

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Reject chat until a Provider-specific adapter is implemented."""
        raise self._unsupported("chat")

    def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Reject streaming until a Provider-specific adapter is implemented."""
        return self._unsupported_stream("streaming")

    async def list_models(self) -> list[ModelInfo]:
        """Reject model listing until a Provider-specific adapter is implemented."""
        raise self._unsupported("model_listing")

    async def test_connection(
        self,
        model_id: str | None = None,
    ) -> ProviderHealthResult:
        """Return a user-safe unsupported result without touching a Provider."""
        error = self._unsupported("chat")
        return ProviderHealthResult(
            status="unhealthy",
            error_code=error.category.value,
            error_message=error.message,
            model_tested=model_id or self._provider_config.default_model,
        )

    def normalize_error(self, error: Exception) -> ProviderAdapterError:
        """Return normalized unsupported or unknown errors."""
        if isinstance(error, ProviderAdapterError):
            return error
        return self._unsupported("unknown")

    async def _unsupported_stream(
        self,
        capability: str,
    ) -> AsyncIterator[ChatChunk]:
        raise self._unsupported(capability)
        yield ChatChunk()

    def _unsupported(self, capability: str) -> ProviderAdapterError:
        return ProviderAdapterError(
            category=ProviderErrorCategory.UNSUPPORTED_FEATURE,
            message="Provider adapter is planned but not implemented.",
            provider_type=self._provider_config.provider_type,
            provider_id=self._provider_config.id,
            retryable=False,
            details={
                "capability": capability,
                "implementation_status": "planned",
            },
        )

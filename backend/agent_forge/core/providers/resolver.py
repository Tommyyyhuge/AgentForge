"""ProviderConfig to ProviderAdapter resolution."""

from collections.abc import Callable

import httpx

from agent_forge.core.providers.adapter import ProviderAdapter
from agent_forge.core.providers.models import (
    ProviderConfig,
    ProviderImplementationStatus,
    ProviderType,
)
from agent_forge.core.providers.official import (
    AnthropicOfficialAdapter,
    DashScopeOfficialAdapter,
    GeminiOfficialAdapter,
    OpenAICompatibleOfficialAdapter,
    OPENAI_COMPATIBLE_OFFICIAL_PROVIDER_TYPES,
)
from agent_forge.core.providers.planned import PlannedProviderAdapter
from agent_forge.core.providers.registry import ProviderRegistry
from agent_forge.core.providers.relay import OpenAICompatibleRelayAdapter

AdapterFactory = Callable[
    [ProviderConfig, str, httpx.AsyncClient | None],
    ProviderAdapter,
]


def _relay_adapter(
    config: ProviderConfig,
    api_key: str,
    http_client: httpx.AsyncClient | None,
) -> ProviderAdapter:
    return OpenAICompatibleRelayAdapter(
        provider_config=config,
        api_key=api_key,
        http_client=http_client,
    )


def _openai_compatible_official_adapter(
    config: ProviderConfig,
    api_key: str,
    http_client: httpx.AsyncClient | None,
) -> ProviderAdapter:
    return OpenAICompatibleOfficialAdapter(
        provider_config=config,
        api_key=api_key,
        http_client=http_client,
    )


def _anthropic_adapter(
    config: ProviderConfig,
    api_key: str,
    http_client: httpx.AsyncClient | None,
) -> ProviderAdapter:
    return AnthropicOfficialAdapter(
        provider_config=config,
        api_key=api_key,
        http_client=http_client,
    )


def _gemini_adapter(
    config: ProviderConfig,
    api_key: str,
    http_client: httpx.AsyncClient | None,
) -> ProviderAdapter:
    return GeminiOfficialAdapter(
        provider_config=config,
        api_key=api_key,
        http_client=http_client,
    )


def _dashscope_adapter(
    config: ProviderConfig,
    api_key: str,
    http_client: httpx.AsyncClient | None,
) -> ProviderAdapter:
    return DashScopeOfficialAdapter(
        provider_config=config,
        api_key=api_key,
        http_client=http_client,
    )


ADAPTER_FACTORIES: dict[ProviderType, AdapterFactory] = {
    ProviderType.OPENAI_COMPATIBLE: _relay_adapter,
    ProviderType.ANTHROPIC: _anthropic_adapter,
    ProviderType.GEMINI: _gemini_adapter,
    ProviderType.DASHSCOPE: _dashscope_adapter,
    **{
        provider_type: _openai_compatible_official_adapter
        for provider_type in OPENAI_COMPATIBLE_OFFICIAL_PROVIDER_TYPES
    },
}


class ProviderAdapterResolver:
    """Resolve validated Provider configs into concrete adapters."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or ProviderRegistry()

    def resolve(
        self,
        provider_config: ProviderConfig,
        *,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> ProviderAdapter:
        """Return a ProviderAdapter for the given ProviderConfig."""
        config = self._registry.validate_config(provider_config)
        provider_type = config.provider_type
        preset = self._registry.get_preset(provider_type)

        if preset.implementation_status == ProviderImplementationStatus.PLANNED:
            return PlannedProviderAdapter(
                provider_config=config,
                allowed_provider_types=frozenset({provider_type}),
            )

        adapter_factory = ADAPTER_FACTORIES.get(provider_type)
        if adapter_factory is not None:
            return adapter_factory(config, api_key, http_client)

        return PlannedProviderAdapter(provider_config=config)

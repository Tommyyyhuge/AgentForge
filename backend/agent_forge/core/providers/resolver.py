"""ProviderConfig to ProviderAdapter resolution."""

import httpx

from agent_forge.core.providers.adapter import ProviderAdapter
from agent_forge.core.providers.models import ProviderConfig, ProviderType
from agent_forge.core.providers.official import (
    AnthropicOfficialAdapter,
    DashScopeOfficialAdapter,
    GeminiOfficialAdapter,
    OpenAICompatibleOfficialAdapter,
    OPENAI_COMPATIBLE_OFFICIAL_PROVIDER_TYPES,
)
from agent_forge.core.providers.planned import (
    PLANNED_PROVIDER_TYPES,
    PlannedProviderAdapter,
)
from agent_forge.core.providers.registry import ProviderRegistry
from agent_forge.core.providers.relay import OpenAICompatibleRelayAdapter


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

        if provider_type == ProviderType.OPENAI_COMPATIBLE:
            return OpenAICompatibleRelayAdapter(
                provider_config=config,
                api_key=api_key,
                http_client=http_client,
            )
        if provider_type in OPENAI_COMPATIBLE_OFFICIAL_PROVIDER_TYPES:
            return OpenAICompatibleOfficialAdapter(
                provider_config=config,
                api_key=api_key,
                http_client=http_client,
            )
        if provider_type == ProviderType.ANTHROPIC:
            return AnthropicOfficialAdapter(
                provider_config=config,
                api_key=api_key,
                http_client=http_client,
            )
        if provider_type == ProviderType.GEMINI:
            return GeminiOfficialAdapter(
                provider_config=config,
                api_key=api_key,
                http_client=http_client,
            )
        if provider_type == ProviderType.DASHSCOPE:
            return DashScopeOfficialAdapter(
                provider_config=config,
                api_key=api_key,
                http_client=http_client,
            )
        if provider_type in PLANNED_PROVIDER_TYPES:
            return PlannedProviderAdapter(provider_config=config)

        return PlannedProviderAdapter(provider_config=config)

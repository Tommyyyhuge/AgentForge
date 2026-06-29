"""OpenAI-compatible relay Provider adapter."""

from agent_forge.core.providers.models import ProviderType
from agent_forge.core.providers.openai_compatible import OpenAICompatibleAdapterBase


class OpenAICompatibleRelayAdapter(OpenAICompatibleAdapterBase):
    """Adapter for OpenAI-compatible relay Providers."""

    allowed_provider_types = frozenset({ProviderType.OPENAI_COMPATIBLE})
    adapter_label = "Relay adapter"

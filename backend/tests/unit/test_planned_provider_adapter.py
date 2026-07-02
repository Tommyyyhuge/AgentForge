"""Planned Provider placeholder adapter tests."""

import pytest

from agent_forge.core.providers import (
    ChatMessage,
    ChatRequest,
    PlannedProviderAdapter,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderConfig,
    ProviderErrorCategory,
    ProviderType,
)


def _planned_config(provider_type: ProviderType) -> ProviderConfig:
    return ProviderConfig(
        id=f"provider-{provider_type.value}",
        provider_type=provider_type,
        display_name=provider_type.value,
        base_url="https://planned.example",
        default_model="planned-model",
        capabilities=ProviderCapabilities(),
    )


@pytest.mark.asyncio
async def test_planned_provider_adapter_rejects_chat_without_routing():
    adapter = PlannedProviderAdapter(
        provider_config=_planned_config(ProviderType.HUNYUAN),
    )

    with pytest.raises(ProviderAdapterError) as exc_info:
        await adapter.chat(
            ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
        )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.UNSUPPORTED_FEATURE
    assert error.provider_type == ProviderType.HUNYUAN
    assert error.provider_id == "provider-hunyuan"
    assert error.details == {
        "capability": "chat",
        "implementation_status": "planned",
    }


@pytest.mark.asyncio
async def test_planned_provider_adapter_rejects_model_listing():
    adapter = PlannedProviderAdapter(
        provider_config=_planned_config(ProviderType.MINIMAX),
    )

    with pytest.raises(ProviderAdapterError) as exc_info:
        await adapter.list_models()

    assert exc_info.value.category == ProviderErrorCategory.UNSUPPORTED_FEATURE
    assert exc_info.value.details == {
        "capability": "model_listing",
        "implementation_status": "planned",
    }

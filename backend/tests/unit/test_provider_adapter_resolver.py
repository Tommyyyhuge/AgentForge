"""Provider adapter resolver tests."""

import httpx

from agent_forge.core.providers import (
    AnthropicOfficialAdapter,
    DashScopeOfficialAdapter,
    GeminiOfficialAdapter,
    OpenAICompatibleAdapterBase,
    OpenAICompatibleOfficialAdapter,
    OpenAICompatibleRelayAdapter,
    PlannedProviderAdapter,
    ProviderAdapterResolver,
    ProviderCapabilities,
    ProviderConfig,
    ProviderImplementationStatus,
    ProviderPreset,
    ProviderRegistry,
    ProviderType,
)


def _config(provider_type: ProviderType) -> ProviderConfig:
    return ProviderConfig(
        id=f"provider-{provider_type.value}",
        provider_type=provider_type,
        display_name=provider_type.value,
        base_url="https://provider.example/v1",
        default_model="model",
        capabilities=ProviderCapabilities(chat=True),
    )


def test_resolver_maps_openai_compatible_relay_provider():
    resolver = ProviderAdapterResolver()
    transport = httpx.MockTransport(lambda request: httpx.Response(200))

    async_client = httpx.AsyncClient(transport=transport)
    adapter = resolver.resolve(
        _config(ProviderType.OPENAI_COMPATIBLE),
        api_key="sk-test",
        http_client=async_client,
    )

    assert isinstance(adapter, OpenAICompatibleRelayAdapter)
    assert isinstance(adapter, OpenAICompatibleAdapterBase)


def test_resolver_maps_openai_compatible_official_providers():
    resolver = ProviderAdapterResolver()
    transport = httpx.MockTransport(lambda request: httpx.Response(200))

    async_client = httpx.AsyncClient(transport=transport)
    for provider_type in {
        ProviderType.OPENAI,
        ProviderType.DEEPSEEK,
        ProviderType.MOONSHOT,
    }:
        adapter = resolver.resolve(
            _config(provider_type),
            api_key="sk-test",
            http_client=async_client,
        )

        assert isinstance(adapter, OpenAICompatibleOfficialAdapter)
        assert isinstance(adapter, OpenAICompatibleAdapterBase)


def test_resolver_maps_dedicated_official_adapters():
    resolver = ProviderAdapterResolver()
    transport = httpx.MockTransport(lambda request: httpx.Response(200))

    async_client = httpx.AsyncClient(transport=transport)
    expected_types = {
        ProviderType.ANTHROPIC: AnthropicOfficialAdapter,
        ProviderType.GEMINI: GeminiOfficialAdapter,
        ProviderType.DASHSCOPE: DashScopeOfficialAdapter,
    }

    for provider_type, adapter_type in expected_types.items():
        adapter = resolver.resolve(
            _config(provider_type),
            api_key="sk-test",
            http_client=async_client,
        )

        assert isinstance(adapter, adapter_type)


def test_resolver_maps_planned_provider_to_placeholder_adapter():
    resolver = ProviderAdapterResolver()
    config = ProviderConfig(
        id="provider-zhipu",
        provider_type=ProviderType.ZHIPU,
        display_name="Zhipu GLM",
        capabilities=ProviderCapabilities(),
    )

    adapter = resolver.resolve(config, api_key="sk-test")

    assert isinstance(adapter, PlannedProviderAdapter)


def test_resolver_honors_registry_planned_status_before_type_mapping():
    registry = ProviderRegistry(
        presets=(
            ProviderPreset(
                provider_type=ProviderType.DASHSCOPE,
                display_name="DashScope planned",
                implementation_status=ProviderImplementationStatus.PLANNED,
                capabilities=ProviderCapabilities(),
            ),
        )
    )
    resolver = ProviderAdapterResolver(registry=registry)
    config = ProviderConfig(
        id="provider-dashscope",
        provider_type=ProviderType.DASHSCOPE,
        display_name="DashScope planned",
        capabilities=ProviderCapabilities(),
    )

    adapter = resolver.resolve(config, api_key="sk-test")

    assert isinstance(adapter, PlannedProviderAdapter)

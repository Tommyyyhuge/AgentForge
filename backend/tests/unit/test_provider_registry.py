"""Provider registry domain model tests."""

import pytest

from agent_forge.core.providers import (
    ModelConfig,
    ProviderCapability,
    ProviderCapabilities,
    ProviderConfig,
    ProviderConfigError,
    ProviderImplementationStatus,
    ProviderRegistry,
    ProviderType,
)


def test_registry_lists_builtin_provider_presets():
    registry = ProviderRegistry()

    presets = registry.list_presets()
    preset_types = {preset.provider_type for preset in presets}

    assert {
        ProviderType.OPENAI,
        ProviderType.ANTHROPIC,
        ProviderType.GEMINI,
        ProviderType.DEEPSEEK,
        ProviderType.MOONSHOT,
        ProviderType.DASHSCOPE,
        ProviderType.OPENAI_COMPATIBLE,
    }.issubset(preset_types)
    assert all(isinstance(preset.capabilities.chat, bool) for preset in presets)


def test_registry_lists_second_batch_as_planned_without_capabilities():
    registry = ProviderRegistry()

    presets = {
        preset.provider_type: preset
        for preset in registry.list_presets()
    }
    planned_provider_types = {
        ProviderType.ZHIPU,
        ProviderType.QIANFAN,
        ProviderType.HUNYUAN,
        ProviderType.MINIMAX,
    }

    assert planned_provider_types.issubset(presets)
    for provider_type in planned_provider_types:
        preset = presets[provider_type]
        assert preset.implementation_status == ProviderImplementationStatus.PLANNED
        assert preset.capabilities == ProviderCapabilities()
        assert preset.official_docs_url is not None


def test_registry_builds_planned_config_without_claiming_capabilities():
    registry = ProviderRegistry()

    config = registry.build_config_from_preset(
        ProviderType.ZHIPU,
        api_key_id="key-zhipu",
    )

    assert config.provider_type == ProviderType.ZHIPU
    assert config.api_key_id == "key-zhipu"
    assert config.capabilities == ProviderCapabilities()
    assert config.streaming_enabled is False
    assert config.tool_calling_enabled is False


def test_registry_capabilities_match_current_official_adapter_support():
    registry = ProviderRegistry()
    presets = {
        preset.provider_type: preset
        for preset in registry.list_presets()
    }

    for provider_type in {
        ProviderType.ANTHROPIC,
        ProviderType.GEMINI,
        ProviderType.DASHSCOPE,
    }:
        capabilities = presets[provider_type].capabilities
        assert capabilities.chat is True
        assert capabilities.streaming is True
        assert capabilities.usage_reporting is True
        assert capabilities.vision is False
        assert capabilities.tool_calling is False
        assert capabilities.json_mode is False
        assert capabilities.model_listing is False


def test_registry_moonshot_preset_uses_openai_compatible_v1_base_url():
    registry = ProviderRegistry()

    preset = registry.get_preset(ProviderType.MOONSHOT)
    config = registry.build_config_from_preset(ProviderType.MOONSHOT)

    assert preset.base_url == "https://api.moonshot.cn/v1"
    assert config.base_url == "https://api.moonshot.cn/v1"


def test_registry_builds_config_from_builtin_preset_without_secret():
    registry = ProviderRegistry()

    config = registry.build_config_from_preset(
        ProviderType.DEEPSEEK,
        api_key_id="key-deepseek",
    )

    assert config.provider_type == ProviderType.DEEPSEEK
    assert config.api_key_id == "key-deepseek"
    assert config.default_model == "deepseek-chat"
    assert config.capabilities.chat is True
    assert "api_key" not in config.model_dump()


def test_registry_validates_openai_compatible_relay_config():
    registry = ProviderRegistry()
    config = ProviderConfig(
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        display_name="Local relay",
        base_url="https://relay.example/v1",
        default_model="gpt-4o-mini",
        capabilities=ProviderCapabilities(chat=True, streaming=True),
    )

    assert registry.validate_config(config) == config


def test_registry_rejects_relay_config_without_base_url_or_model():
    registry = ProviderRegistry()
    config = ProviderConfig(
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        display_name="Broken relay",
        capabilities=ProviderCapabilities(chat=True),
    )

    with pytest.raises(ProviderConfigError) as exc_info:
        registry.validate_config(config)

    assert exc_info.value.code == "provider_invalid_request"
    assert exc_info.value.details["provider_type"] == "openai_compatible"


def test_model_capability_overrides_provider_capability():
    registry = ProviderRegistry()
    provider_config = ProviderConfig(
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        display_name="Relay",
        base_url="https://relay.example/v1",
        default_model="manual-model",
        capabilities=ProviderCapabilities(chat=True, streaming=True),
    )
    model_config = ModelConfig(
        provider_id="provider-1",
        model_id="manual-model",
        supports_streaming=False,
    )

    assert (
        registry.supports_capability(
            provider_config,
            ProviderCapability.STREAMING,
            model_config=model_config,
        )
        is False
    )

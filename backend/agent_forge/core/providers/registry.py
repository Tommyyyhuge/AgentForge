"""Provider registry and config validation."""

from agent_forge.core.providers.models import (
    ModelConfig,
    ProviderCapability,
    ProviderCapabilities,
    ProviderConfig,
    ProviderConfigError,
    ProviderImplementationStatus,
    ProviderPreset,
    ProviderType,
)

MODEL_CAPABILITY_FIELDS: dict[ProviderCapability, str] = {
    ProviderCapability.STREAMING: "supports_streaming",
    ProviderCapability.TOOL_CALLING: "supports_tool_calling",
    ProviderCapability.JSON_MODE: "supports_json_mode",
    ProviderCapability.VISION: "supports_vision",
    ProviderCapability.EMBEDDINGS: "supports_embeddings",
}


def _chat_only(**overrides: bool) -> ProviderCapabilities:
    values = {"chat": True, **overrides}
    return ProviderCapabilities(**values)


BUILTIN_PROVIDER_PRESETS: tuple[ProviderPreset, ...] = (
    ProviderPreset(
        provider_type=ProviderType.OPENAI,
        display_name="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        capabilities=_chat_only(
            streaming=True,
            tool_calling=True,
            json_mode=True,
            vision=True,
            embeddings=True,
            model_listing=True,
            usage_reporting=True,
        ),
    ),
    ProviderPreset(
        provider_type=ProviderType.ANTHROPIC,
        display_name="Anthropic Claude",
        base_url="https://api.anthropic.com",
        default_model="claude-3-5-sonnet-latest",
        capabilities=_chat_only(streaming=True, usage_reporting=True),
    ),
    ProviderPreset(
        provider_type=ProviderType.GEMINI,
        display_name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com",
        default_model="gemini-1.5-flash",
        capabilities=_chat_only(streaming=True, usage_reporting=True),
    ),
    ProviderPreset(
        provider_type=ProviderType.DEEPSEEK,
        display_name="DeepSeek",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        capabilities=_chat_only(streaming=True, usage_reporting=True),
    ),
    ProviderPreset(
        provider_type=ProviderType.MOONSHOT,
        display_name="Moonshot/Kimi",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        capabilities=_chat_only(streaming=True, usage_reporting=True),
        aliases=("kimi",),
    ),
    ProviderPreset(
        provider_type=ProviderType.DASHSCOPE,
        display_name="Alibaba DashScope/Qwen",
        base_url="https://dashscope.aliyuncs.com",
        default_model="qwen-plus",
        capabilities=_chat_only(streaming=True, usage_reporting=True),
    ),
    ProviderPreset(
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        display_name="OpenAI-compatible relay",
        default_model=None,
        capabilities=_chat_only(),
        is_relay=True,
    ),
    ProviderPreset(
        provider_type=ProviderType.ZHIPU,
        display_name="Zhipu GLM",
        implementation_status=ProviderImplementationStatus.PLANNED,
        official_docs_url="https://docs.bigmodel.cn/",
        capabilities=ProviderCapabilities(),
    ),
    ProviderPreset(
        provider_type=ProviderType.QIANFAN,
        display_name="Baidu Qianfan",
        implementation_status=ProviderImplementationStatus.PLANNED,
        official_docs_url=(
            "https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html"
        ),
        capabilities=ProviderCapabilities(),
    ),
    ProviderPreset(
        provider_type=ProviderType.HUNYUAN,
        display_name="Tencent Hunyuan",
        implementation_status=ProviderImplementationStatus.PLANNED,
        official_docs_url="https://cloud.tencent.com/document/product/1729",
        capabilities=ProviderCapabilities(),
    ),
    ProviderPreset(
        provider_type=ProviderType.MINIMAX,
        display_name="MiniMax",
        implementation_status=ProviderImplementationStatus.PLANNED,
        official_docs_url="https://platform.minimaxi.com/document",
        capabilities=ProviderCapabilities(),
    ),
)


class ProviderRegistry:
    """Registry for built-in Provider presets and config validation."""

    def __init__(
        self,
        presets: tuple[ProviderPreset, ...] = BUILTIN_PROVIDER_PRESETS,
    ) -> None:
        self._presets = {preset.provider_type: preset for preset in presets}

    def list_presets(self) -> list[ProviderPreset]:
        """Return built-in Provider presets in stable provider_type order."""
        return [
            self._presets[provider_type]
            for provider_type in sorted(self._presets, key=lambda item: item.value)
        ]

    def get_preset(self, provider_type: ProviderType) -> ProviderPreset:
        """Return a preset or raise a user-safe validation error."""
        try:
            return self._presets[provider_type]
        except KeyError as exc:
            raise ProviderConfigError(
                code="provider_invalid_request",
                message="Unsupported provider type.",
                details={"provider_type": provider_type.value},
            ) from exc

    def build_config_from_preset(
        self,
        provider_type: ProviderType,
        *,
        api_key_id: str | None = None,
        display_name: str | None = None,
    ) -> ProviderConfig:
        """Create a runtime config from built-in preset metadata."""
        preset = self.get_preset(provider_type)
        config = ProviderConfig(
            provider_type=preset.provider_type,
            display_name=display_name or preset.display_name,
            base_url=preset.base_url,
            auth_type=preset.auth_type,
            api_key_id=api_key_id,
            default_model=preset.default_model,
            capabilities=preset.capabilities,
            streaming_enabled=preset.capabilities.streaming,
            tool_calling_enabled=preset.capabilities.tool_calling,
        )
        return self.validate_config(config)

    def validate_config(self, config: ProviderConfig) -> ProviderConfig:
        """Validate provider config before persistence or adapter resolution."""
        if config.provider_type == ProviderType.OPENAI_COMPATIBLE:
            self._validate_relay_config(config)
            return config

        preset = self.get_preset(config.provider_type)
        if preset.implementation_status == ProviderImplementationStatus.PLANNED:
            if config.capabilities != ProviderCapabilities():
                raise ProviderConfigError(
                    code="provider_unsupported_feature",
                    message="Planned provider config cannot claim capabilities.",
                    details={"provider_type": config.provider_type.value},
                )
            return config

        if not config.default_model:
            raise ProviderConfigError(
                code="provider_invalid_request",
                message="Provider config requires a default model.",
                details={"provider_type": config.provider_type.value},
            )
        return config

    def supports_capability(
        self,
        provider_config: ProviderConfig,
        capability: ProviderCapability,
        *,
        model_config: ModelConfig | None = None,
    ) -> bool:
        """Resolve capability with model-level overrides when present."""
        override_field = MODEL_CAPABILITY_FIELDS.get(capability)
        if override_field and model_config is not None:
            override_value = getattr(model_config, override_field)
            if override_value is not None:
                return bool(override_value)
        return provider_config.capabilities.supports(capability)

    def _validate_relay_config(self, config: ProviderConfig) -> None:
        details = {"provider_type": config.provider_type.value}
        if not config.base_url or not config.base_url.startswith(("http://", "https://")):
            raise ProviderConfigError(
                code="provider_invalid_request",
                message="Relay provider requires an HTTP base URL.",
                details=details,
            )
        if not config.default_model:
            raise ProviderConfigError(
                code="provider_invalid_request",
                message="Relay provider requires a default model.",
                details=details,
            )
        if not config.capabilities.chat:
            raise ProviderConfigError(
                code="provider_invalid_request",
                message="Relay provider must support chat completions.",
                details=details,
            )

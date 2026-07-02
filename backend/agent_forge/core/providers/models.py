"""Provider registry domain models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Known provider type identifiers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    DASHSCOPE = "dashscope"
    ZHIPU = "zhipu"
    QIANFAN = "qianfan"
    HUNYUAN = "hunyuan"
    MINIMAX = "minimax"
    OPENAI_COMPATIBLE = "openai_compatible"


class AuthType(str, Enum):
    """Supported provider authentication styles."""

    API_KEY_BEARER = "api_key_bearer"
    API_KEY_HEADER = "api_key_header"
    NONE = "none"


class ProviderCapability(str, Enum):
    """Capability names shared by registry, adapters, and execution code."""

    CHAT = "chat"
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    JSON_MODE = "json_mode"
    VISION = "vision"
    EMBEDDINGS = "embeddings"
    MODEL_LISTING = "model_listing"
    USAGE_REPORTING = "usage_reporting"


class ProviderImplementationStatus(str, Enum):
    """Implementation state exposed by built-in Provider presets."""

    IMPLEMENTED = "implemented"
    PLANNED = "planned"


class ProviderCapabilities(BaseModel):
    """Provider-level capability flags.

    Flags default to False so execution code never assumes support implicitly.
    """

    chat: bool = False
    streaming: bool = False
    tool_calling: bool = False
    json_mode: bool = False
    vision: bool = False
    embeddings: bool = False
    model_listing: bool = False
    usage_reporting: bool = False

    def supports(self, capability: ProviderCapability) -> bool:
        return bool(getattr(self, capability.value))


class ProviderPreset(BaseModel):
    """Built-in provider metadata exposed by the registry."""

    provider_type: ProviderType
    display_name: str
    base_url: str | None = None
    default_model: str | None = None
    implementation_status: ProviderImplementationStatus = (
        ProviderImplementationStatus.IMPLEMENTED
    )
    official_docs_url: str | None = None
    auth_type: AuthType = AuthType.API_KEY_BEARER
    capabilities: ProviderCapabilities = Field(
        default_factory=ProviderCapabilities
    )
    aliases: tuple[str, ...] = ()
    is_relay: bool = False


class ProviderConfig(BaseModel):
    """Runtime provider config.

    This is a domain model, not an ORM record. Persistence is introduced by
    AF-005.
    """

    id: str | None = None
    provider_type: ProviderType
    display_name: str
    base_url: str | None = None
    auth_type: AuthType = AuthType.API_KEY_BEARER
    api_key_id: str | None = None
    default_model: str | None = None
    capabilities: ProviderCapabilities = Field(
        default_factory=ProviderCapabilities
    )
    timeout_seconds: int = 60
    rate_limit_policy: dict[str, Any] = Field(default_factory=dict)
    streaming_enabled: bool = False
    tool_calling_enabled: bool = False
    is_active: bool = True


class ModelConfig(BaseModel):
    """Model-level provider config.

    Optional supports_* fields can override provider-level capabilities when a
    model is known to differ from the provider default.
    """

    id: str | None = None
    provider_id: str
    model_id: str
    display_name: str | None = None
    context_window: int | None = None
    supports_streaming: bool | None = None
    supports_tool_calling: bool | None = None
    supports_json_mode: bool | None = None
    supports_vision: bool | None = None
    supports_embeddings: bool | None = None
    is_default: bool = False
    is_active: bool = True


class ProviderConfigError(ValueError):
    """User-safe provider config validation error."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

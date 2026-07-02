"""Provider settings routes."""

from typing import Any, Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.api.middleware.auth import get_current_active_user
from agent_forge.api.responses import success_response
from agent_forge.config.settings import settings
from agent_forge.core.providers import (
    AuthType,
    ModelInfo,
    ProviderAdapterError,
    ProviderAdapterResolver,
    ProviderCapabilities,
    ProviderConfig,
    ProviderConfigError,
    ProviderErrorCategory,
    ProviderHealthResult,
    ProviderPreset,
    ProviderRegistry,
    ProviderType,
)
from agent_forge.core.providers.service import ProviderConfigService
from agent_forge.database.connection import get_db
from agent_forge.database.models import APIKeyORM, UserORM
from agent_forge.utils.encryption import APIKeyEncryption


router = APIRouter(prefix="/providers", tags=["providers"])
provider_registry = ProviderRegistry()
provider_config_service = ProviderConfigService(provider_registry)
provider_adapter_resolver = ProviderAdapterResolver(provider_registry)
T = TypeVar("T")


class _CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SuccessEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None


class CreateProviderConfigRequest(_CamelModel):
    provider_type: ProviderType = Field(..., alias="providerType")
    display_name: str = Field(..., min_length=1, alias="displayName")
    base_url: str | None = Field(default=None, alias="baseUrl")
    auth_type: AuthType = Field(
        default=AuthType.API_KEY_BEARER,
        alias="authType",
    )
    api_key_id: str | None = Field(default=None, alias="apiKeyId")
    default_model: str | None = Field(default=None, alias="defaultModel")
    capabilities: ProviderCapabilities = Field(
        default_factory=ProviderCapabilities
    )
    timeout_seconds: int = Field(default=60, ge=1, le=300, alias="timeoutSeconds")
    rate_limit_policy: dict[str, Any] = Field(
        default_factory=dict,
        alias="rateLimitPolicy",
    )
    streaming_enabled: bool = Field(default=False, alias="streamingEnabled")
    tool_calling_enabled: bool = Field(
        default=False,
        alias="toolCallingEnabled",
    )


class UpdateProviderConfigRequest(_CamelModel):
    provider_type: ProviderType | None = Field(default=None, alias="providerType")
    display_name: str | None = Field(
        default=None,
        min_length=1,
        alias="displayName",
    )
    base_url: str | None = Field(default=None, alias="baseUrl")
    auth_type: AuthType | None = Field(default=None, alias="authType")
    api_key_id: str | None = Field(default=None, alias="apiKeyId")
    default_model: str | None = Field(default=None, alias="defaultModel")
    capabilities: ProviderCapabilities | None = None
    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        le=300,
        alias="timeoutSeconds",
    )
    rate_limit_policy: dict[str, Any] | None = Field(
        default=None,
        alias="rateLimitPolicy",
    )
    streaming_enabled: bool | None = Field(
        default=None,
        alias="streamingEnabled",
    )
    tool_calling_enabled: bool | None = Field(
        default=None,
        alias="toolCallingEnabled",
    )


class ProviderTestRequest(_CamelModel):
    model_id: str | None = Field(default=None, alias="modelId")


class ProviderPresetResponse(_CamelModel):
    provider_type: ProviderType = Field(alias="providerType")
    display_name: str = Field(alias="displayName")
    base_url: str | None = Field(default=None, alias="baseUrl")
    default_model: str | None = Field(default=None, alias="defaultModel")
    implementation_status: str = Field(alias="implementationStatus")
    official_docs_url: str | None = Field(default=None, alias="officialDocsUrl")
    auth_type: AuthType = Field(alias="authType")
    capabilities: ProviderCapabilities
    aliases: list[str] = Field(default_factory=list)
    is_relay: bool = Field(alias="isRelay")


class ProviderConfigResponse(_CamelModel):
    id: str | None
    provider_type: ProviderType = Field(alias="providerType")
    display_name: str = Field(alias="displayName")
    base_url: str | None = Field(default=None, alias="baseUrl")
    auth_type: AuthType = Field(alias="authType")
    api_key_id: str | None = Field(default=None, alias="apiKeyId")
    default_model: str | None = Field(default=None, alias="defaultModel")
    capabilities: ProviderCapabilities
    timeout_seconds: int = Field(alias="timeoutSeconds")
    rate_limit_policy: dict[str, Any] = Field(alias="rateLimitPolicy")
    streaming_enabled: bool = Field(alias="streamingEnabled")
    tool_calling_enabled: bool = Field(alias="toolCallingEnabled")
    is_active: bool = Field(alias="isActive")


class ProviderModelResponse(_CamelModel):
    id: str
    display_name: str | None = Field(default=None, alias="displayName")


class ProviderHealthResponse(_CamelModel):
    status: str
    latency_ms: int | None = Field(default=None, alias="latencyMs")
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    model_tested: str | None = Field(default=None, alias="modelTested")


class ProviderErrorSummaryResponse(_CamelModel):
    code: str
    message: str
    retryable: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderModelsResponse(_CamelModel):
    status: str
    models: list[ProviderModelResponse]
    manual_entry_allowed: bool = Field(alias="manualEntryAllowed")
    error: ProviderErrorSummaryResponse | None = None


def _get_encryption() -> APIKeyEncryption:
    return APIKeyEncryption(
        master_key=settings.ENCRYPTION_KEY.get_secret_value(),
        salt=settings.ENCRYPTION_SALT.get_secret_value(),
    )


def _preset_to_response(preset: ProviderPreset) -> ProviderPresetResponse:
    return ProviderPresetResponse(
        providerType=preset.provider_type,
        displayName=preset.display_name,
        baseUrl=preset.base_url,
        defaultModel=preset.default_model,
        implementationStatus=preset.implementation_status.value,
        officialDocsUrl=preset.official_docs_url,
        authType=preset.auth_type,
        capabilities=preset.capabilities,
        aliases=list(preset.aliases),
        isRelay=preset.is_relay,
    )


def _config_to_response(config: ProviderConfig) -> ProviderConfigResponse:
    return ProviderConfigResponse(
        id=config.id,
        providerType=config.provider_type,
        displayName=config.display_name,
        baseUrl=config.base_url,
        authType=config.auth_type,
        apiKeyId=config.api_key_id,
        defaultModel=config.default_model,
        capabilities=config.capabilities,
        timeoutSeconds=config.timeout_seconds,
        rateLimitPolicy=config.rate_limit_policy,
        streamingEnabled=config.streaming_enabled,
        toolCallingEnabled=config.tool_calling_enabled,
        isActive=config.is_active,
    )


def _model_to_response(model: ModelInfo) -> ProviderModelResponse:
    return ProviderModelResponse(
        id=model.id,
        displayName=model.display_name,
    )


def _health_to_response(result: ProviderHealthResult) -> ProviderHealthResponse:
    return ProviderHealthResponse(
        status=result.status,
        latencyMs=result.latency_ms,
        errorCode=result.error_code,
        errorMessage=result.error_message,
        modelTested=result.model_tested,
    )


def _adapter_error_to_response(
    error: ProviderAdapterError,
) -> ProviderErrorSummaryResponse:
    return ProviderErrorSummaryResponse(
        code=error.category.value,
        message=error.message,
        retryable=error.retryable,
        details=error.details,
    )


def _raise_config_error(error: ProviderConfigError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": error.code,
            "message": error.message,
            "details": error.details,
        },
    )


async def _get_provider_or_404(
    provider_id: str,
    db: AsyncSession,
) -> ProviderConfig:
    config = await provider_config_service.get_config(db, provider_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider config not found.",
        )
    return config


async def _get_api_key_secret(
    provider_config: ProviderConfig,
    user: UserORM,
    db: AsyncSession,
) -> str:
    if provider_config.auth_type == AuthType.NONE:
        return ""
    if not provider_config.api_key_id:
        raise ProviderAdapterError(
            category=ProviderErrorCategory.AUTH_FAILED,
            message="Provider API key is not configured.",
            provider_type=provider_config.provider_type,
            provider_id=provider_config.id,
        )

    result = await db.execute(
        select(APIKeyORM).where(
            APIKeyORM.id == provider_config.api_key_id,
            APIKeyORM.user_id == user.id,
            APIKeyORM.is_active.is_(True),
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise ProviderAdapterError(
            category=ProviderErrorCategory.AUTH_FAILED,
            message="Provider API key is not available.",
            provider_type=provider_config.provider_type,
            provider_id=provider_config.id,
        )

    try:
        return _get_encryption().decrypt(key.encrypted_key)
    except Exception as exc:
        raise ProviderAdapterError(
            category=ProviderErrorCategory.AUTH_FAILED,
            message="Provider API key could not be read.",
            provider_type=provider_config.provider_type,
            provider_id=provider_config.id,
        ) from exc


async def _resolve_adapter(
    provider_config: ProviderConfig,
    user: UserORM,
    db: AsyncSession,
):
    api_key = await _get_api_key_secret(provider_config, user, db)
    return provider_adapter_resolver.resolve(provider_config, api_key=api_key)


@router.get(
    "/presets",
    response_model=SuccessEnvelope[list[ProviderPresetResponse]],
)
async def list_provider_presets(
    user: UserORM = Depends(get_current_active_user),
):
    return success_response(
        [
            _preset_to_response(preset)
            for preset in provider_registry.list_presets()
        ]
    )


@router.get("", response_model=SuccessEnvelope[list[ProviderConfigResponse]])
async def list_provider_configs(
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    configs = await provider_config_service.list_configs(db)
    return success_response([_config_to_response(config) for config in configs])


@router.post(
    "",
    response_model=SuccessEnvelope[ProviderConfigResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_provider_config(
    request: CreateProviderConfigRequest,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        config = ProviderConfig(**request.model_dump(by_alias=False))
        created = await provider_config_service.create_config(db, config)
    except ProviderConfigError as exc:
        _raise_config_error(exc)
    return success_response(_config_to_response(created))


@router.get("/{provider_id}", response_model=SuccessEnvelope[ProviderConfigResponse])
async def get_provider_config(
    provider_id: str,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_provider_or_404(provider_id, db)
    return success_response(_config_to_response(config))


@router.patch(
    "/{provider_id}",
    response_model=SuccessEnvelope[ProviderConfigResponse],
)
async def update_provider_config(
    provider_id: str,
    request: UpdateProviderConfigRequest,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    updates = request.model_dump(exclude_unset=True, by_alias=False)
    try:
        updated = await provider_config_service.update_config(
            db,
            provider_id,
            updates,
        )
    except ProviderConfigError as exc:
        _raise_config_error(exc)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider config not found.",
        )
    return success_response(_config_to_response(updated))


@router.delete(
    "/{provider_id}",
    response_model=SuccessEnvelope[ProviderConfigResponse],
)
async def delete_provider_config(
    provider_id: str,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await provider_config_service.delete_config(db, provider_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider config not found.",
        )
    return success_response(
        _config_to_response(deleted),
        message="Provider config deleted.",
    )


@router.post(
    "/{provider_id}/test",
    response_model=SuccessEnvelope[ProviderHealthResponse],
)
async def test_provider_config(
    provider_id: str,
    request: ProviderTestRequest,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_provider_or_404(provider_id, db)
    try:
        adapter = await _resolve_adapter(config, user, db)
        result = await adapter.test_connection(request.model_id)
    except ProviderAdapterError as exc:
        result = ProviderHealthResult(
            status="unhealthy",
            error_code=exc.category.value,
            error_message=exc.message,
            model_tested=request.model_id or config.default_model,
        )
    return success_response(_health_to_response(result))


@router.get(
    "/{provider_id}/models",
    response_model=SuccessEnvelope[ProviderModelsResponse],
)
async def list_provider_models(
    provider_id: str,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_provider_or_404(provider_id, db)
    try:
        adapter = await _resolve_adapter(config, user, db)
        models = await adapter.list_models()
        data = ProviderModelsResponse(
            status="available",
            models=[_model_to_response(model) for model in models],
            manualEntryAllowed=True,
            error=None,
        )
    except ProviderAdapterError as exc:
        data = ProviderModelsResponse(
            status="degraded",
            models=[],
            manualEntryAllowed=True,
            error=_adapter_error_to_response(exc),
        )
    return success_response(data)

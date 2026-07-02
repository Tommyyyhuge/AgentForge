"""Provider config persistence service."""

from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.core.providers.models import (
    AuthType,
    ProviderCapabilities,
    ProviderConfig,
    ProviderConfigError,
    ProviderType,
)
from agent_forge.core.providers.registry import ProviderRegistry
from agent_forge.database.models import APIKeyORM, ProviderConfigORM


LEGACY_API_KEY_PROVIDER_TYPES: dict[str, ProviderType] = {
    "kimi": ProviderType.MOONSHOT,
    "deepseek": ProviderType.DEEPSEEK,
}


class ProviderConfigService:
    """Create and query persisted Provider configs."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or ProviderRegistry()

    async def create_config(
        self,
        db: AsyncSession,
        config: ProviderConfig,
    ) -> ProviderConfig:
        """Validate and persist a Provider config."""
        validated = self._registry.validate_config(config)
        record = ProviderConfigORM(
            id=validated.id,
            provider_type=validated.provider_type.value,
            display_name=validated.display_name,
            base_url=validated.base_url,
            auth_type=validated.auth_type.value,
            api_key_id=validated.api_key_id,
            default_model=validated.default_model,
            capabilities=validated.capabilities.model_dump(),
            timeout_seconds=validated.timeout_seconds,
            rate_limit_policy=validated.rate_limit_policy,
            streaming_enabled=validated.streaming_enabled,
            tool_calling_enabled=validated.tool_calling_enabled,
            is_active=validated.is_active,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return self._to_domain(record)

    async def get_config(
        self,
        db: AsyncSession,
        provider_config_id: str,
    ) -> ProviderConfig | None:
        """Return an active Provider config by id."""
        result = await db.execute(
            select(ProviderConfigORM).where(
                ProviderConfigORM.id == provider_config_id,
                ProviderConfigORM.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        return self._to_domain(record)

    async def list_configs(self, db: AsyncSession) -> list[ProviderConfig]:
        """List active Provider configs ordered by creation time."""
        result = await db.execute(
            select(ProviderConfigORM)
            .where(ProviderConfigORM.is_active.is_(True))
            .order_by(ProviderConfigORM.created_at.asc())
        )
        return [self._to_domain(record) for record in result.scalars().all()]

    async def update_config(
        self,
        db: AsyncSession,
        provider_config_id: str,
        updates: dict[str, Any],
    ) -> ProviderConfig | None:
        """Validate and update an active Provider config."""
        result = await db.execute(
            select(ProviderConfigORM).where(
                ProviderConfigORM.id == provider_config_id,
                ProviderConfigORM.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        data = self._to_domain(record).model_dump()
        data.update(updates)
        try:
            candidate = ProviderConfig(**data)
        except ValidationError as exc:
            raise ProviderConfigError(
                code="provider_invalid_request",
                message="Provider config is invalid.",
                details={
                    "errors": [
                        {
                            "loc": error.get("loc", ()),
                            "type": error.get("type", "value_error"),
                        }
                        for error in exc.errors()
                    ]
                },
            ) from exc
        validated = self._registry.validate_config(candidate)

        record.provider_type = validated.provider_type.value
        record.display_name = validated.display_name
        record.base_url = validated.base_url
        record.auth_type = validated.auth_type.value
        record.api_key_id = validated.api_key_id
        record.default_model = validated.default_model
        record.capabilities = validated.capabilities.model_dump()
        record.timeout_seconds = validated.timeout_seconds
        record.rate_limit_policy = validated.rate_limit_policy
        record.streaming_enabled = validated.streaming_enabled
        record.tool_calling_enabled = validated.tool_calling_enabled
        record.is_active = validated.is_active
        record.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(record)
        return self._to_domain(record)

    async def delete_config(
        self,
        db: AsyncSession,
        provider_config_id: str,
    ) -> ProviderConfig | None:
        """Soft-delete an active Provider config."""
        result = await db.execute(
            select(ProviderConfigORM).where(
                ProviderConfigORM.id == provider_config_id,
                ProviderConfigORM.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        record.is_active = False
        record.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(record)
        return self._to_domain(record)

    async def bootstrap_from_api_keys(
        self,
        db: AsyncSession,
        user_id: str | None = None,
    ) -> list[ProviderConfig]:
        """Create preset Provider configs for existing legacy API keys."""
        query = select(APIKeyORM).where(
            APIKeyORM.provider.in_(list(LEGACY_API_KEY_PROVIDER_TYPES)),
            APIKeyORM.is_active.is_(True),
            APIKeyORM.permission == "write",
        )
        if user_id:
            query = query.where(APIKeyORM.user_id == user_id)

        result = await db.execute(query)
        keys = list(result.scalars().all())
        configs: list[ProviderConfig] = []

        for provider_name in LEGACY_API_KEY_PROVIDER_TYPES:
            for key in [item for item in keys if item.provider == provider_name]:
                existing = await self._get_active_config_for_api_key(db, key.id)
                if existing:
                    configs.append(existing)
                    continue

                preset_type = LEGACY_API_KEY_PROVIDER_TYPES[provider_name]
                config = self._registry.build_config_from_preset(
                    preset_type,
                    api_key_id=key.id,
                )
                configs.append(await self.create_config(db, config))

        return configs

    def _to_domain(self, record: ProviderConfigORM) -> ProviderConfig:
        return ProviderConfig(
            id=record.id,
            provider_type=ProviderType(record.provider_type),
            display_name=record.display_name,
            base_url=record.base_url,
            auth_type=AuthType(record.auth_type),
            api_key_id=record.api_key_id,
            default_model=record.default_model,
            capabilities=ProviderCapabilities(**(record.capabilities or {})),
            timeout_seconds=record.timeout_seconds,
            rate_limit_policy=record.rate_limit_policy or {},
            streaming_enabled=record.streaming_enabled,
            tool_calling_enabled=record.tool_calling_enabled,
            is_active=record.is_active,
        )

    async def _get_active_config_for_api_key(
        self,
        db: AsyncSession,
        api_key_id: str,
    ) -> ProviderConfig | None:
        result = await db.execute(
            select(ProviderConfigORM).where(
                ProviderConfigORM.api_key_id == api_key_id,
                ProviderConfigORM.is_active.is_(True),
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        return self._to_domain(record)

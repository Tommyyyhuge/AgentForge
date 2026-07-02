"""Provider config service tests."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_forge.core.providers import (
    ProviderCapabilities,
    ProviderConfig,
    ProviderConfigError,
    ProviderType,
)
from agent_forge.core.providers.service import ProviderConfigService
from agent_forge.database.connection import Base
from agent_forge.database.models import APIKeyORM, ProviderConfigORM, UserORM


async def _create_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def test_provider_service_creates_gets_and_lists_provider_configs():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            service = ProviderConfigService()
            created = await service.create_config(
                session,
                ProviderConfig(
                    provider_type=ProviderType.OPENAI_COMPATIBLE,
                    display_name="Local relay",
                    base_url="https://relay.example/v1",
                    default_model="gpt-4o-mini",
                    capabilities=ProviderCapabilities(chat=True, streaming=True),
                    streaming_enabled=True,
                ),
            )

            fetched = await service.get_config(session, created.id or "")
            configs = await service.list_configs(session)

            assert created.id is not None
            assert fetched is not None
            assert fetched.provider_type == ProviderType.OPENAI_COMPATIBLE
            assert fetched.capabilities.streaming is True
            assert [config.id for config in configs] == [created.id]
    finally:
        await engine.dispose()


async def test_provider_service_rejects_invalid_config_before_persisting():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            service = ProviderConfigService()
            with pytest.raises(ProviderConfigError):
                await service.create_config(
                    session,
                    ProviderConfig(
                        provider_type=ProviderType.OPENAI_COMPATIBLE,
                        display_name="Broken relay",
                        capabilities=ProviderCapabilities(chat=True),
                    ),
                )

            rows = (
                await session.execute(select(ProviderConfigORM))
            ).scalars().all()
            assert rows == []
    finally:
        await engine.dispose()


async def test_provider_service_updates_and_soft_deletes_provider_configs():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            service = ProviderConfigService()
            created = await service.create_config(
                session,
                ProviderConfig(
                    provider_type=ProviderType.OPENAI_COMPATIBLE,
                    display_name="Local relay",
                    base_url="https://relay.example/v1",
                    default_model="gpt-4o-mini",
                    capabilities=ProviderCapabilities(chat=True),
                ),
            )

            updated = await service.update_config(
                session,
                created.id or "",
                {
                    "default_model": "gpt-4.1-mini",
                    "capabilities": ProviderCapabilities(
                        chat=True,
                        streaming=True,
                    ),
                    "streaming_enabled": True,
                },
            )
            deleted = await service.delete_config(session, created.id or "")
            fetched_after_delete = await service.get_config(session, created.id or "")
            listed_after_delete = await service.list_configs(session)

            assert updated is not None
            assert updated.default_model == "gpt-4.1-mini"
            assert updated.capabilities.streaming is True
            assert updated.streaming_enabled is True
            assert deleted is not None
            assert deleted.is_active is False
            assert fetched_after_delete is None
            assert listed_after_delete == []
    finally:
        await engine.dispose()


async def test_provider_service_bootstraps_legacy_kimi_and_deepseek_keys():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            session.add_all(
                [
                    UserORM(
                        id="user-1",
                        username="user",
                        email="user@example.com",
                        hashed_password="hashed",
                    ),
                    APIKeyORM(
                        id="key-kimi",
                        user_id="user-1",
                        provider="kimi",
                        encrypted_key="encrypted-kimi",
                        masked_key="sk-****kimi",
                    ),
                    APIKeyORM(
                        id="key-deepseek",
                        user_id="user-1",
                        provider="deepseek",
                        encrypted_key="encrypted-deepseek",
                        masked_key="sk-****seek",
                    ),
                    APIKeyORM(
                        id="key-read-only",
                        user_id="user-1",
                        provider="kimi",
                        encrypted_key="encrypted-read",
                        masked_key="sk-****read",
                        permission="read",
                    ),
                    APIKeyORM(
                        id="key-unsupported",
                        user_id="user-1",
                        provider="unknown",
                        encrypted_key="encrypted-unknown",
                        masked_key="sk-****nown",
                    ),
                ]
            )
            await session.commit()

            service = ProviderConfigService()
            first_bootstrap = await service.bootstrap_from_api_keys(session)
            second_bootstrap = await service.bootstrap_from_api_keys(session)

            assert [config.api_key_id for config in first_bootstrap] == [
                "key-kimi",
                "key-deepseek",
            ]
            assert [config.provider_type for config in first_bootstrap] == [
                ProviderType.MOONSHOT,
                ProviderType.DEEPSEEK,
            ]
            assert [config.default_model for config in first_bootstrap] == [
                "moonshot-v1-8k",
                "deepseek-chat",
            ]
            assert [config.id for config in second_bootstrap] == [
                config.id for config in first_bootstrap
            ]

            rows = (
                await session.execute(select(ProviderConfigORM))
            ).scalars().all()
            assert len(rows) == 2
    finally:
        await engine.dispose()

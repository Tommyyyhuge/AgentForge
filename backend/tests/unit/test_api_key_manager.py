"""API key manager tests."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_forge.core.api_key_manager import APIKeyManager
from agent_forge.database.connection import Base
from agent_forge.database.models import APIKeyORM, ProviderConfigORM, UserORM


class FakeEncryption:
    def decrypt(self, ciphertext: str) -> str:
        secrets = {
            "encrypted-secret": "sk-provider-secret",
            "encrypted-moonshot": "sk-moonshot-secret",
            "encrypted-openai": "sk-openai-secret",
        }
        if ciphertext in secrets:
            return secrets[ciphertext]
        raise ValueError("cannot decrypt")


async def _create_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def test_get_key_for_provider_config_returns_decrypted_key_and_tracks_usage():
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
                        id="key-1",
                        user_id="user-1",
                        provider="deepseek",
                        encrypted_key="encrypted-secret",
                        masked_key="sk-****cret",
                    ),
                    ProviderConfigORM(
                        id="provider-1",
                        provider_type="deepseek",
                        display_name="DeepSeek",
                        api_key_id="key-1",
                        default_model="deepseek-chat",
                        capabilities={"chat": True},
                    ),
                ]
            )
            await session.commit()

            manager = APIKeyManager(FakeEncryption())  # type: ignore[arg-type]
            key = await manager.get_key_for_provider_config(
                "provider-1",
                session,
                user_id="user-1",
            )

            assert key == "sk-provider-secret"

        async with sessionmaker() as session:
            stored_key = (
                await session.execute(
                    select(APIKeyORM).where(APIKeyORM.id == "key-1")
                )
            ).scalar_one()
            assert stored_key.usage_count == 1
            assert stored_key.last_used_at is not None
    finally:
        await engine.dispose()


async def test_get_key_for_provider_config_rejects_other_users_key():
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
                    UserORM(
                        id="user-2",
                        username="other",
                        email="other@example.com",
                        hashed_password="hashed",
                    ),
                    APIKeyORM(
                        id="key-1",
                        user_id="user-1",
                        provider="deepseek",
                        encrypted_key="encrypted-secret",
                        masked_key="sk-****cret",
                    ),
                    ProviderConfigORM(
                        id="provider-1",
                        provider_type="deepseek",
                        display_name="DeepSeek",
                        api_key_id="key-1",
                        default_model="deepseek-chat",
                        capabilities={"chat": True},
                    ),
                ]
            )
            await session.commit()

            manager = APIKeyManager(FakeEncryption())  # type: ignore[arg-type]
            key = await manager.get_key_for_provider_config(
                "provider-1",
                session,
                user_id="user-2",
            )

            assert key is None
    finally:
        await engine.dispose()


async def test_get_key_resolves_provider_type_alias_to_legacy_key():
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
                        encrypted_key="encrypted-moonshot",
                        masked_key="sk-****shot",
                    ),
                ]
            )
            await session.commit()

            manager = APIKeyManager(FakeEncryption())  # type: ignore[arg-type]
            key = await manager.get_key("moonshot", session, user_id="user-1")

            assert key == "sk-moonshot-secret"

        async with sessionmaker() as session:
            stored_key = (
                await session.execute(
                    select(APIKeyORM).where(APIKeyORM.id == "key-kimi")
                )
            ).scalar_one()
            assert stored_key.usage_count == 1
            assert stored_key.last_used_at is not None
    finally:
        await engine.dispose()


async def test_get_all_keys_uses_provider_registry_and_keeps_kimi_compatibility():
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
                        id="key-moonshot",
                        user_id="user-1",
                        provider="moonshot",
                        encrypted_key="encrypted-moonshot",
                        masked_key="sk-****shot",
                    ),
                    APIKeyORM(
                        id="key-openai",
                        user_id="user-1",
                        provider="openai",
                        encrypted_key="encrypted-openai",
                        masked_key="sk-****open",
                    ),
                    APIKeyORM(
                        id="key-unknown",
                        user_id="user-1",
                        provider="unknown",
                        encrypted_key="encrypted-secret",
                        masked_key="sk-****cret",
                    ),
                ]
            )
            await session.commit()

            manager = APIKeyManager(FakeEncryption())  # type: ignore[arg-type]
            keys = await manager.get_all_keys(session, user_id="user-1")

            assert keys == {
                "kimi": "sk-moonshot-secret",
                "openai": "sk-openai-secret",
            }
    finally:
        await engine.dispose()

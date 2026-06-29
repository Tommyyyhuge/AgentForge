"""API key route tests."""

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_forge.api.routes import keys as key_routes
from agent_forge.database.connection import Base
from agent_forge.database.models import APIKeyORM, ProviderConfigORM, UserORM


async def _create_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _user() -> UserORM:
    return UserORM(
        id="user-1",
        username="user",
        email="user@example.com",
        hashed_password="hashed",
    )


async def test_list_keys_filters_by_provider_and_includes_provider_config_links():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            user = _user()
            session.add_all(
                [
                    user,
                    APIKeyORM(
                        id="key-deepseek",
                        user_id=user.id,
                        provider="deepseek",
                        encrypted_key="encrypted-deepseek",
                        masked_key="sk-****seek",
                    ),
                    APIKeyORM(
                        id="key-kimi",
                        user_id=user.id,
                        provider="kimi",
                        encrypted_key="encrypted-kimi",
                        masked_key="sk-****kimi",
                    ),
                    ProviderConfigORM(
                        id="provider-deepseek",
                        provider_type="deepseek",
                        display_name="DeepSeek",
                        api_key_id="key-deepseek",
                        default_model="deepseek-chat",
                        capabilities={"chat": True},
                    ),
                ]
            )
            await session.commit()

            response = await key_routes.list_keys(
                provider="deepseek",
                user=user,
                db=session,
            )

            assert response["success"] is True
            assert [item["id"] for item in response["data"]] == ["key-deepseek"]
            assert response["data"][0]["linked_provider_config_count"] == 1
            assert response["data"][0]["linked_provider_configs"] == [
                {
                    "id": "provider-deepseek",
                    "display_name": "DeepSeek",
                    "provider_type": "deepseek",
                }
            ]
            assert "encrypted-deepseek" not in str(response)
    finally:
        await engine.dispose()


async def test_delete_key_reports_linked_provider_config_impact():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            user = _user()
            session.add_all(
                [
                    user,
                    APIKeyORM(
                        id="key-deepseek",
                        user_id=user.id,
                        provider="deepseek",
                        encrypted_key="encrypted-deepseek",
                        masked_key="sk-****seek",
                    ),
                    ProviderConfigORM(
                        id="provider-deepseek",
                        provider_type="deepseek",
                        display_name="DeepSeek",
                        api_key_id="key-deepseek",
                        default_model="deepseek-chat",
                        capabilities={"chat": True},
                    ),
                ]
            )
            await session.commit()

            response = await key_routes.delete_key(
                key_id="key-deepseek",
                user=user,
                db=session,
            )

            assert response["success"] is True
            assert response["data"]["linked_provider_config_count"] == 1
            assert response["data"]["linked_provider_configs"] == [
                {
                    "id": "provider-deepseek",
                    "display_name": "DeepSeek",
                    "provider_type": "deepseek",
                }
            ]
            assert "Provider config" in response["message"]
            assert "encrypted-deepseek" not in str(response)

            stored_key = (
                await session.execute(
                    select(APIKeyORM).where(APIKeyORM.id == "key-deepseek")
                )
            ).scalar_one()
            assert stored_key.is_active is False
    finally:
        await engine.dispose()


async def test_create_key_rejects_unknown_provider_without_storing_secret():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            user = _user()
            session.add(user)
            await session.commit()

            with pytest.raises(HTTPException) as exc_info:
                await key_routes.create_key(
                    request=key_routes.CreateKeyRequest(
                        provider="website_automation",
                        api_key="sk-secret-value",
                    ),
                    user=user,
                    db=session,
                )

            assert exc_info.value.status_code == 400
            assert "sk-secret-value" not in str(exc_info.value.detail)
            rows = (await session.execute(select(APIKeyORM))).scalars().all()
            assert rows == []
    finally:
        await engine.dispose()

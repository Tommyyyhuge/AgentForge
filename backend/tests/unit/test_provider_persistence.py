"""Provider persistence ORM tests."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_forge.database.connection import Base
from agent_forge.database.models import (
    APIKeyORM,
    ModelConfigORM,
    ProviderConfigORM,
    ProviderHealthCheckORM,
    UserORM,
)


def test_provider_tables_are_registered_in_metadata():
    tables = Base.metadata.tables

    assert "provider_configs" in tables
    assert "model_configs" in tables
    assert "provider_health_checks" in tables
    assert "provider_capabilities" not in tables

    provider_columns = tables["provider_configs"].columns
    assert "capabilities" in provider_columns
    assert "api_key_id" in provider_columns

    model_columns = tables["model_configs"].columns
    assert "supports_streaming" in model_columns
    assert "supports_tool_calling" in model_columns
    assert "supports_json_mode" in model_columns
    assert "supports_vision" in model_columns
    assert "supports_embeddings" in model_columns


async def test_provider_config_model_and_health_check_round_trip_sqlite():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with sessionmaker() as session:
        user = UserORM(
            id="user-1",
            username="user",
            email="user@example.com",
            hashed_password="hashed",
        )
        api_key = APIKeyORM(
            id="key-1",
            user_id="user-1",
            provider="deepseek",
            encrypted_key="encrypted",
            masked_key="sk-****-test",
        )
        provider = ProviderConfigORM(
            id="provider-1",
            provider_type="deepseek",
            display_name="DeepSeek",
            base_url="https://api.deepseek.com",
            api_key_id="key-1",
            default_model="deepseek-chat",
            capabilities={"chat": True, "streaming": True},
            streaming_enabled=True,
        )
        model = ModelConfigORM(
            id="model-1",
            provider_id="provider-1",
            model_id="deepseek-chat",
            supports_streaming=True,
            is_default=True,
        )
        health_check = ProviderHealthCheckORM(
            id="health-1",
            provider_id="provider-1",
            status="healthy",
            latency_ms=120,
            model_tested="deepseek-chat",
        )

        session.add_all([user, api_key, provider, model, health_check])
        await session.commit()

    async with sessionmaker() as session:
        stored = (
            await session.execute(
                select(ProviderConfigORM).where(
                    ProviderConfigORM.id == "provider-1"
                )
            )
        ).scalar_one()

        assert stored.api_key_id == "key-1"
        assert stored.capabilities == {"chat": True, "streaming": True}
        assert stored.models[0].model_id == "deepseek-chat"
        assert stored.health_checks[0].status == "healthy"

    await engine.dispose()

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import agent_forge.database.connection as connection_module
from agent_forge.database.connection import Base
from agent_forge.database.models import APIKeyORM, ProviderConfigORM, UserORM


@pytest.mark.asyncio
async def test_init_db_runs_migrations_then_provider_bootstrap_without_create_all(
    monkeypatch,
):
    calls = []

    def fake_upgrade(config, revision):
        calls.append(("upgrade", revision))

    async def fake_bootstrap_provider_configs():
        calls.append(("bootstrap_provider_configs", None))

    class ForbiddenEngine:
        def begin(self):
            raise AssertionError("init_db must not create schema outside Alembic")

    monkeypatch.setattr("alembic.command.upgrade", fake_upgrade)
    monkeypatch.setattr(
        connection_module,
        "bootstrap_provider_configs",
        fake_bootstrap_provider_configs,
    )
    monkeypatch.setattr(connection_module, "engine", ForbiddenEngine())

    await connection_module.init_db()

    assert calls == [("upgrade", "head"), ("bootstrap_provider_configs", None)]


@pytest.mark.asyncio
async def test_bootstrap_provider_configs_from_existing_keys(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(connection_module, "async_session", sessionmaker)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as session:
            session.add(
                UserORM(
                    id="user-1",
                    username="user1",
                    email="user1@example.com",
                    hashed_password="hashed",
                )
            )
            session.add_all(
                [
                    APIKeyORM(
                        id="key-kimi",
                        user_id="user-1",
                        provider="kimi",
                        encrypted_key="encrypted-kimi",
                        masked_key="sk-****-kimi",
                        permission="write",
                        is_active=True,
                    ),
                    APIKeyORM(
                        id="key-deepseek",
                        user_id="user-1",
                        provider="deepseek",
                        encrypted_key="encrypted-deepseek",
                        masked_key="sk-****-deep",
                        permission="write",
                        is_active=True,
                    ),
                ]
            )
            await session.commit()

        await connection_module.bootstrap_provider_configs()

        async with sessionmaker() as session:
            result = await session.execute(
                select(ProviderConfigORM).order_by(
                    ProviderConfigORM.provider_type.asc()
                )
            )
            rows = list(result.scalars().all())

        assert [row.api_key_id for row in rows] == ["key-deepseek", "key-kimi"]
        assert [row.provider_type for row in rows] == ["deepseek", "moonshot"]
    finally:
        await engine.dispose()

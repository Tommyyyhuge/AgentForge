"""Provider route tests."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from main import app
from agent_forge.api.routes import providers as provider_routes
from agent_forge.core.providers import (
    ModelInfo,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderConfig,
    ProviderErrorCategory,
    ProviderHealthResult,
    ProviderType,
)
from agent_forge.database.connection import Base
from agent_forge.database.models import ProviderConfigORM, UserORM


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


def test_provider_routes_require_authentication():
    response = TestClient(app).get("/api/v1/providers")

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_provider_routes_publish_pydantic_response_schemas():
    schema_names = set(TestClient(app).app.openapi()["components"]["schemas"])

    assert "ProviderConfigResponse" in schema_names
    assert "ProviderPresetResponse" in schema_names
    assert "ProviderModelsResponse" in schema_names
    assert "ProviderHealthResponse" in schema_names


async def test_list_provider_presets_returns_standard_envelope_without_secrets():
    response = await provider_routes.list_provider_presets(user=_user())

    assert response["success"] is True
    provider_types = {item["providerType"] for item in response["data"]}
    assert ProviderType.OPENAI_COMPATIBLE.value in provider_types
    assert ProviderType.MOONSHOT.value in provider_types
    assert response["data"][0]["capabilities"]
    assert "sk-secret" not in str(response)


async def test_provider_routes_create_get_patch_list_and_delete_configs():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            user = _user()
            create_response = await provider_routes.create_provider_config(
                request=provider_routes.CreateProviderConfigRequest(
                    provider_type=ProviderType.OPENAI_COMPATIBLE,
                    display_name="Local relay",
                    base_url="https://relay.example/v1",
                    default_model="gpt-4o-mini",
                    capabilities=ProviderCapabilities(chat=True),
                ),
                user=user,
                db=session,
            )

            created = create_response["data"]
            get_response = await provider_routes.get_provider_config(
                provider_id=created["id"],
                user=user,
                db=session,
            )
            update_response = await provider_routes.update_provider_config(
                provider_id=created["id"],
                request=provider_routes.UpdateProviderConfigRequest(
                    default_model="gpt-4.1-mini",
                    capabilities=ProviderCapabilities(chat=True, streaming=True),
                    streaming_enabled=True,
                ),
                user=user,
                db=session,
            )
            list_response = await provider_routes.list_provider_configs(
                user=user,
                db=session,
            )
            delete_response = await provider_routes.delete_provider_config(
                provider_id=created["id"],
                user=user,
                db=session,
            )
            list_after_delete = await provider_routes.list_provider_configs(
                user=user,
                db=session,
            )

            assert create_response["success"] is True
            assert created["providerType"] == ProviderType.OPENAI_COMPATIBLE.value
            assert get_response["data"]["id"] == created["id"]
            assert update_response["data"]["defaultModel"] == "gpt-4.1-mini"
            assert update_response["data"]["streamingEnabled"] is True
            assert [item["id"] for item in list_response["data"]] == [created["id"]]
            assert delete_response["data"]["isActive"] is False
            assert list_after_delete["data"] == []
    finally:
        await engine.dispose()


async def test_create_provider_config_rejects_invalid_relay_config_without_storing():
    engine, sessionmaker = await _create_sessionmaker()

    try:
        async with sessionmaker() as session:
            with pytest.raises(HTTPException) as exc_info:
                await provider_routes.create_provider_config(
                    request=provider_routes.CreateProviderConfigRequest(
                        provider_type=ProviderType.OPENAI_COMPATIBLE,
                        display_name="Broken relay",
                        capabilities=ProviderCapabilities(chat=True),
                    ),
                    user=_user(),
                    db=session,
                )

            assert exc_info.value.status_code == 400
            assert "secret" not in str(exc_info.value.detail).lower()
            rows = (await session.execute(select(ProviderConfigORM))).scalars().all()
            assert rows == []
    finally:
        await engine.dispose()


async def test_provider_test_route_returns_normalized_failure(monkeypatch):
    engine, sessionmaker = await _create_sessionmaker()

    class FailingTestAdapter:
        async def test_connection(
            self,
            model_id: str | None = None,
        ) -> ProviderHealthResult:
            return ProviderHealthResult(
                status="unhealthy",
                error_code=ProviderErrorCategory.AUTH_FAILED.value,
                error_message="Provider authentication failed.",
                model_tested=model_id,
            )

    class Resolver:
        def resolve(self, provider_config: ProviderConfig, *, api_key: str):
            return FailingTestAdapter()

    try:
        async with sessionmaker() as session:
            user = _user()
            create_response = await provider_routes.create_provider_config(
                request=provider_routes.CreateProviderConfigRequest(
                    provider_type=ProviderType.OPENAI_COMPATIBLE,
                    display_name="Local relay",
                    base_url="https://relay.example/v1",
                    default_model="gpt-4o-mini",
                    capabilities=ProviderCapabilities(chat=True),
                ),
                user=user,
                db=session,
            )
            provider_id = create_response["data"]["id"]
            monkeypatch.setattr(
                provider_routes,
                "_get_api_key_secret",
                AsyncMock(return_value="sk-secret-value"),
            )
            monkeypatch.setattr(
                provider_routes,
                "provider_adapter_resolver",
                Resolver(),
            )

            response = await provider_routes.test_provider_config(
                provider_id=provider_id,
                request=provider_routes.ProviderTestRequest(model_id="gpt-test"),
                user=user,
                db=session,
            )

            assert response["success"] is True
            assert response["data"]["status"] == "unhealthy"
            assert response["data"]["errorCode"] == "provider_auth_failed"
            assert response["data"]["modelTested"] == "gpt-test"
            assert "sk-secret-value" not in str(response)
    finally:
        await engine.dispose()


async def test_provider_models_route_degrades_when_model_listing_fails(monkeypatch):
    engine, sessionmaker = await _create_sessionmaker()

    class FailingModelsAdapter:
        async def list_models(self) -> list[ModelInfo]:
            raise ProviderAdapterError(
                category=ProviderErrorCategory.AUTH_FAILED,
                message="Provider authentication failed.",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            )

    class Resolver:
        def resolve(self, provider_config: ProviderConfig, *, api_key: str):
            return FailingModelsAdapter()

    try:
        async with sessionmaker() as session:
            user = _user()
            create_response = await provider_routes.create_provider_config(
                request=provider_routes.CreateProviderConfigRequest(
                    provider_type=ProviderType.OPENAI_COMPATIBLE,
                    display_name="Local relay",
                    base_url="https://relay.example/v1",
                    default_model="gpt-4o-mini",
                    capabilities=ProviderCapabilities(chat=True),
                ),
                user=user,
                db=session,
            )
            provider_id = create_response["data"]["id"]
            monkeypatch.setattr(
                provider_routes,
                "_get_api_key_secret",
                AsyncMock(return_value="sk-secret-value"),
            )
            monkeypatch.setattr(
                provider_routes,
                "provider_adapter_resolver",
                Resolver(),
            )

            response = await provider_routes.list_provider_models(
                provider_id=provider_id,
                user=user,
                db=session,
            )

            assert response["success"] is True
            assert response["data"]["status"] == "degraded"
            assert response["data"]["manualEntryAllowed"] is True
            assert response["data"]["models"] == []
            assert response["data"]["error"]["code"] == "provider_auth_failed"
            assert "sk-secret-value" not in str(response)
    finally:
        await engine.dispose()

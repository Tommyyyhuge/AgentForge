"""Official Provider adapter tests."""

import json

import httpx
import pytest

from agent_forge.core.providers import (
    ChatMessage,
    ChatRequest,
    OpenAICompatibleOfficialAdapter,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderConfig,
    ProviderErrorCategory,
    ProviderType,
)


def _config(
    provider_type: ProviderType,
    *,
    base_url: str,
    default_model: str,
) -> ProviderConfig:
    return ProviderConfig(
        id=f"provider-{provider_type.value}",
        provider_type=provider_type,
        display_name=provider_type.value,
        base_url=base_url,
        default_model=default_model,
        capabilities=ProviderCapabilities(
            chat=True,
            streaming=True,
            model_listing=True,
            usage_reporting=True,
        ),
        streaming_enabled=True,
    )


@pytest.mark.asyncio
async def test_openai_compatible_official_adapter_maps_supported_provider_chat():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer sk-official"
        assert body["model"] == "deepseek-chat"
        assert body["messages"] == [{"role": "user", "content": "Ping"}]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenAICompatibleOfficialAdapter(
            provider_config=_config(
                ProviderType.DEEPSEEK,
                base_url="https://api.deepseek.com",
                default_model="deepseek-chat",
            ),
            api_key="sk-official",
            http_client=client,
        )

        response = await adapter.chat(
            ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
        )

    assert str(requests[0].url) == "https://api.deepseek.com/chat/completions"
    assert response.content == "pong"
    assert response.usage is not None
    assert response.usage.total_tokens == 2


@pytest.mark.asyncio
async def test_openai_compatible_official_adapter_rejects_non_compatible_provider():
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError):
            OpenAICompatibleOfficialAdapter(
                provider_config=_config(
                    ProviderType.ANTHROPIC,
                    base_url="https://api.anthropic.com",
                    default_model="claude-test",
                ),
                api_key="sk-official",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_openai_compatible_official_adapter_redacts_provider_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "error": {
                    "message": "model missing sk-official",
                    "code": "model_not_found",
                }
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenAICompatibleOfficialAdapter(
            provider_config=_config(
                ProviderType.MOONSHOT,
                base_url="https://api.moonshot.cn/v1",
                default_model="moonshot-v1-8k",
            ),
            api_key="sk-official",
            http_client=client,
        )

        with pytest.raises(ProviderAdapterError) as exc_info:
            await adapter.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
            )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.MODEL_NOT_FOUND
    assert error.provider_type == ProviderType.MOONSHOT
    assert error.provider_id == "provider-moonshot"
    assert "sk-official" not in error.message
    assert "sk-official" not in str(error.details)

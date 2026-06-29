"""OpenAI-compatible relay adapter tests."""

import json

import httpx
import pytest

from agent_forge.core.providers import (
    ProviderCapabilities,
    ProviderConfig,
    ProviderType,
)
from agent_forge.core.providers.adapter import (
    ChatMessage,
    ChatRequest,
    ProviderAdapterError,
    ProviderErrorCategory,
)
from agent_forge.core.providers.relay import OpenAICompatibleRelayAdapter


def _relay_config() -> ProviderConfig:
    return ProviderConfig(
        id="provider-relay",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        display_name="Local relay",
        base_url="https://relay.example/v1",
        default_model="gpt-4o-mini",
        capabilities=ProviderCapabilities(
            chat=True,
            streaming=True,
            model_listing=True,
            usage_reporting=True,
        ),
        streaming_enabled=True,
    )


@pytest.mark.asyncio
async def test_relay_adapter_maps_chat_request_and_response():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert request.method == "POST"
        assert str(request.url) == "https://relay.example/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer sk-test"
        assert body == {
            "messages": [{"role": "user", "content": "Say hi"}],
            "model": "gpt-4o-mini",
            "stream": False,
        }
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "hi"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenAICompatibleRelayAdapter(
            provider_config=_relay_config(),
            api_key="sk-test",
            http_client=client,
        )

        response = await adapter.chat(
            ChatRequest(messages=[ChatMessage(role="user", content="Say hi")])
        )

    assert response.content == "hi"
    assert response.finish_reason == "stop"
    assert response.usage is not None
    assert response.usage.prompt_tokens == 3
    assert response.usage.total_tokens == 5
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_relay_adapter_streams_openai_compatible_chunks():
    stream_body = "\n\n".join(
        [
            'data: {"choices":[{"delta":{"content":"he"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"llo"},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}',
            "data: [DONE]",
        ]
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(200, text=stream_body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenAICompatibleRelayAdapter(
            provider_config=_relay_config(),
            api_key="sk-test",
            http_client=client,
        )

        chunks = [
            chunk
            async for chunk in adapter.stream(
                ChatRequest(
                    messages=[ChatMessage(role="user", content="Say hi")],
                    model="manual-model",
                )
            )
        ]

    assert [chunk.content_delta for chunk in chunks] == ["he", "llo"]
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage is not None
    assert chunks[-1].usage.total_tokens == 3


@pytest.mark.asyncio
async def test_relay_adapter_normalizes_http_errors_without_secret_leakage():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"message": "invalid api key sk-test"}},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenAICompatibleRelayAdapter(
            provider_config=_relay_config(),
            api_key="sk-test",
            http_client=client,
        )

        with pytest.raises(ProviderAdapterError) as exc_info:
            await adapter.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="Say hi")])
            )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.AUTH_FAILED
    assert error.provider_type == ProviderType.OPENAI_COMPATIBLE
    assert error.provider_id == "provider-relay"
    assert error.retryable is False
    assert "sk-test" not in error.message
    assert "sk-test" not in str(error.details)


@pytest.mark.asyncio
async def test_relay_adapter_lists_models_and_tests_connection():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert str(request.url) == "https://relay.example/v1/models"
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "gpt-4o-mini", "owned_by": "relay"},
                        {"id": "manual-model"},
                    ]
                },
            )

        body = json.loads(request.content)
        assert body["model"] == "manual-model"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenAICompatibleRelayAdapter(
            provider_config=_relay_config(),
            api_key="sk-test",
            http_client=client,
        )

        models = await adapter.list_models()
        health = await adapter.test_connection("manual-model")

    assert [model.id for model in models] == ["gpt-4o-mini", "manual-model"]
    assert models[0].display_name == "gpt-4o-mini"
    assert health.status == "healthy"
    assert health.model_tested == "manual-model"

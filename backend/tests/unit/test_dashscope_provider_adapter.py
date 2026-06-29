"""Alibaba DashScope/Qwen official Provider adapter tests."""

import json

import httpx
import pytest

from agent_forge.core.providers import (
    ChatMessage,
    ChatRequest,
    DashScopeOfficialAdapter,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderConfig,
    ProviderErrorCategory,
    ProviderType,
)


def _dashscope_config() -> ProviderConfig:
    return ProviderConfig(
        id="provider-dashscope",
        provider_type=ProviderType.DASHSCOPE,
        display_name="Alibaba DashScope/Qwen",
        base_url="https://dashscope.aliyuncs.com",
        default_model="qwen-plus",
        capabilities=ProviderCapabilities(
            chat=True,
            streaming=True,
            usage_reporting=True,
        ),
        streaming_enabled=True,
    )


@pytest.mark.asyncio
async def test_dashscope_adapter_maps_chat_request_and_response():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert request.method == "POST"
        assert (
            str(request.url)
            == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        )
        assert request.headers["authorization"] == "Bearer sk-ds-test"
        assert body == {
            "messages": [{"role": "user", "content": "Ping"}],
            "model": "qwen-plus",
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 16,
        }
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
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DashScopeOfficialAdapter(
            provider_config=_dashscope_config(),
            api_key="sk-ds-test",
            http_client=client,
        )

        response = await adapter.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content="Ping")],
                temperature=0.3,
                max_tokens=16,
            )
        )

    assert len(requests) == 1
    assert response.content == "pong"
    assert response.finish_reason == "stop"
    assert response.usage is not None
    assert response.usage.total_tokens == 5


@pytest.mark.asyncio
async def test_dashscope_adapter_streams_chunks_with_usage_enabled():
    stream_body = "\n\n".join(
        [
            'data: {"choices":[{"delta":{"content":"he"},"finish_reason":null}]}',
            (
                'data: {"choices":[{"delta":{"content":"llo"},'
                '"finish_reason":"stop"}],'
                '"usage":{"prompt_tokens":2,"completion_tokens":2,'
                '"total_tokens":4}}'
            ),
            "data: [DONE]",
        ]
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        assert body["stream_options"] == {"include_usage": True}
        return httpx.Response(200, text=stream_body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DashScopeOfficialAdapter(
            provider_config=_dashscope_config(),
            api_key="sk-ds-test",
            http_client=client,
        )

        chunks = [
            chunk
            async for chunk in adapter.stream(
                ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
            )
        ]

    assert [chunk.content_delta for chunk in chunks] == ["he", "llo"]
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage is not None
    assert chunks[-1].usage.total_tokens == 4


@pytest.mark.asyncio
async def test_dashscope_adapter_rejects_non_dashscope_config():
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError):
            DashScopeOfficialAdapter(
                provider_config=ProviderConfig(
                    id="provider-openai",
                    provider_type=ProviderType.OPENAI,
                    display_name="OpenAI",
                    base_url="https://api.openai.com/v1",
                    default_model="gpt-4o-mini",
                ),
                api_key="sk-ds-test",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_dashscope_adapter_redacts_provider_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "error": {
                    "message": "Invalid API key sk-ds-test",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                }
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DashScopeOfficialAdapter(
            provider_config=_dashscope_config(),
            api_key="sk-ds-test",
            http_client=client,
        )

        with pytest.raises(ProviderAdapterError) as exc_info:
            await adapter.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
            )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.AUTH_FAILED
    assert error.provider_type == ProviderType.DASHSCOPE
    assert error.provider_id == "provider-dashscope"
    assert "sk-ds-test" not in error.message
    assert "sk-ds-test" not in str(error.details)

"""Anthropic official Provider adapter tests."""

import json

import httpx
import pytest

from agent_forge.core.providers import (
    AnthropicOfficialAdapter,
    ChatMessage,
    ChatRequest,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderConfig,
    ProviderErrorCategory,
    ProviderType,
)


def _anthropic_config(*, streaming_enabled: bool = True) -> ProviderConfig:
    return ProviderConfig(
        id="provider-anthropic",
        provider_type=ProviderType.ANTHROPIC,
        display_name="Anthropic Claude",
        base_url="https://api.anthropic.com",
        default_model="claude-3-5-sonnet-latest",
        capabilities=ProviderCapabilities(
            chat=True,
            streaming=True,
            usage_reporting=True,
        ),
        streaming_enabled=streaming_enabled,
    )


@pytest.mark.asyncio
async def test_anthropic_adapter_maps_chat_request_and_response():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == "sk-ant-test"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert body == {
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "Ping"}],
            "system": "Be terse.",
        }
        return httpx.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "pong"},
                    {"type": "text", "text": "!"},
                ],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 4, "output_tokens": 2},
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = AnthropicOfficialAdapter(
            provider_config=_anthropic_config(),
            api_key="sk-ant-test",
            http_client=client,
        )

        response = await adapter.chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="system", content="Be terse."),
                    ChatMessage(role="user", content="Ping"),
                ],
                max_tokens=16,
            )
        )

    assert len(requests) == 1
    assert response.content == "pong!"
    assert response.finish_reason == "end_turn"
    assert response.usage is not None
    assert response.usage.prompt_tokens == 4
    assert response.usage.completion_tokens == 2
    assert response.usage.total_tokens == 6


@pytest.mark.asyncio
async def test_anthropic_adapter_streams_text_deltas():
    stream_body = "\n\n".join(
        [
            (
                'data: {"type":"content_block_delta",'
                '"delta":{"type":"text_delta","text":"he"}}'
            ),
            (
                'data: {"type":"message_delta",'
                '"delta":{"stop_reason":"end_turn"},'
                '"usage":{"output_tokens":2}}'
            ),
            'data: {"type":"message_stop"}',
        ]
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(200, text=stream_body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = AnthropicOfficialAdapter(
            provider_config=_anthropic_config(),
            api_key="sk-ant-test",
            http_client=client,
        )

        chunks = [
            chunk
            async for chunk in adapter.stream(
                ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
            )
        ]

    assert [chunk.content_delta for chunk in chunks] == ["he", ""]
    assert chunks[-1].finish_reason == "end_turn"
    assert chunks[-1].usage is not None
    assert chunks[-1].usage.completion_tokens == 2


@pytest.mark.asyncio
async def test_anthropic_adapter_rejects_openai_specific_request_fields():
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = AnthropicOfficialAdapter(
            provider_config=_anthropic_config(),
            api_key="sk-ant-test",
            http_client=client,
        )

        with pytest.raises(ProviderAdapterError) as exc_info:
            await adapter.chat(
                ChatRequest(
                    messages=[ChatMessage(role="user", content="Ping")],
                    response_format={"type": "json_object"},
                )
            )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.UNSUPPORTED_FEATURE
    assert error.provider_type == ProviderType.ANTHROPIC
    assert error.details == {"capability": "json_mode"}


@pytest.mark.asyncio
async def test_anthropic_adapter_redacts_provider_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "type": "error",
                "error": {
                    "type": "rate_limit_error",
                    "message": "rate limited for sk-ant-test",
                },
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = AnthropicOfficialAdapter(
            provider_config=_anthropic_config(),
            api_key="sk-ant-test",
            http_client=client,
        )

        with pytest.raises(ProviderAdapterError) as exc_info:
            await adapter.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
            )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.RATE_LIMITED
    assert error.retryable is True
    assert "sk-ant-test" not in error.message
    assert "sk-ant-test" not in str(error.details)

"""Google Gemini official Provider adapter tests."""

import json

import httpx
import pytest

from agent_forge.core.providers import (
    ChatMessage,
    ChatRequest,
    GeminiOfficialAdapter,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderConfig,
    ProviderErrorCategory,
    ProviderType,
)


def _gemini_config(*, streaming_enabled: bool = True) -> ProviderConfig:
    return ProviderConfig(
        id="provider-gemini",
        provider_type=ProviderType.GEMINI,
        display_name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com",
        default_model="gemini-1.5-flash",
        capabilities=ProviderCapabilities(
            chat=True,
            streaming=True,
            usage_reporting=True,
        ),
        streaming_enabled=streaming_enabled,
    )


@pytest.mark.asyncio
async def test_gemini_adapter_maps_chat_request_and_response():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert request.method == "POST"
        assert (
            str(request.url)
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=sk-gem-test"
        )
        assert body == {
            "contents": [
                {"role": "user", "parts": [{"text": "Ping"}]},
            ],
            "systemInstruction": {"parts": [{"text": "Be terse."}]},
            "generationConfig": {
                "maxOutputTokens": 16,
                "temperature": 0.2,
            },
        }
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "pong"},
                                {"text": "!"},
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 4,
                    "candidatesTokenCount": 2,
                    "totalTokenCount": 6,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiOfficialAdapter(
            provider_config=_gemini_config(),
            api_key="sk-gem-test",
            http_client=client,
        )

        response = await adapter.chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="system", content="Be terse."),
                    ChatMessage(role="user", content="Ping"),
                ],
                max_tokens=16,
                temperature=0.2,
            )
        )

    assert len(requests) == 1
    assert response.content == "pong!"
    assert response.finish_reason == "STOP"
    assert response.usage is not None
    assert response.usage.prompt_tokens == 4
    assert response.usage.completion_tokens == 2
    assert response.usage.total_tokens == 6


@pytest.mark.asyncio
async def test_gemini_adapter_streams_text_deltas():
    stream_body = "\n".join(
        [
            json.dumps(
                {
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "he"}]},
                            "finishReason": None,
                        }
                    ]
                }
            ),
            json.dumps(
                {
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "llo"}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 2,
                        "candidatesTokenCount": 2,
                        "totalTokenCount": 4,
                    },
                }
            ),
        ]
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert str(request.url).endswith(
            "/v1beta/models/gemini-1.5-flash:streamGenerateContent?key=sk-gem-test"
        )
        assert "contents" in body
        return httpx.Response(200, text=stream_body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiOfficialAdapter(
            provider_config=_gemini_config(),
            api_key="sk-gem-test",
            http_client=client,
        )

        chunks = [
            chunk
            async for chunk in adapter.stream(
                ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
            )
        ]

    assert [chunk.content_delta for chunk in chunks] == ["he", "llo"]
    assert chunks[-1].finish_reason == "STOP"
    assert chunks[-1].usage is not None
    assert chunks[-1].usage.total_tokens == 4


@pytest.mark.asyncio
async def test_gemini_adapter_rejects_tool_calling_until_mapped():
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiOfficialAdapter(
            provider_config=_gemini_config(),
            api_key="sk-gem-test",
            http_client=client,
        )

        with pytest.raises(ProviderAdapterError) as exc_info:
            await adapter.chat(
                ChatRequest(
                    messages=[ChatMessage(role="user", content="Ping")],
                    tools=[{"type": "function"}],
                )
            )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.UNSUPPORTED_FEATURE
    assert error.provider_type == ProviderType.GEMINI
    assert error.details == {"capability": "tool_calling"}


@pytest.mark.asyncio
async def test_gemini_adapter_redacts_provider_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "code": 403,
                    "message": "API key sk-gem-test is invalid",
                    "status": "PERMISSION_DENIED",
                }
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiOfficialAdapter(
            provider_config=_gemini_config(),
            api_key="sk-gem-test",
            http_client=client,
        )

        with pytest.raises(ProviderAdapterError) as exc_info:
            await adapter.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="Ping")])
            )

    error = exc_info.value
    assert error.category == ProviderErrorCategory.AUTH_FAILED
    assert error.provider_id == "provider-gemini"
    assert "sk-gem-test" not in error.message
    assert "sk-gem-test" not in str(error.details)

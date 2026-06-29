import { describe, expect, it } from 'vitest'
import {
  DEFAULT_PROVIDER_CAPABILITIES,
  toProviderConfig,
  toProviderHealthResult,
  toProviderModelsResult,
  toProviderPreset,
} from '../../src/api/providers'

describe('provider API mapping', () => {
  it('maps Provider presets into typed frontend objects', () => {
    expect(
      toProviderPreset({
        providerType: 'openai_compatible',
        displayName: 'OpenAI-compatible relay',
        implementationStatus: 'implemented',
        authType: 'api_key_bearer',
        capabilities: { chat: true, streaming: true },
        aliases: [],
        isRelay: true,
      }),
    ).toMatchObject({
      providerType: 'openai_compatible',
      displayName: 'OpenAI-compatible relay',
      implementationStatus: 'implemented',
      isRelay: true,
      capabilities: {
        ...DEFAULT_PROVIDER_CAPABILITIES,
        chat: true,
        streaming: true,
      },
    })
  })

  it('maps Provider configs without exposing API key plaintext', () => {
    const config = toProviderConfig({
      id: 'provider-1',
      providerType: 'openai_compatible',
      displayName: 'Local relay',
      baseUrl: 'https://relay.example/v1',
      authType: 'api_key_bearer',
      apiKeyId: 'key-1',
      defaultModel: 'gpt-4o-mini',
      capabilities: { chat: true },
      timeoutSeconds: 60,
      rateLimitPolicy: {},
      streamingEnabled: false,
      toolCallingEnabled: false,
      isActive: true,
      apiKey: 'sk-secret',
    })

    expect(config).toEqual({
      id: 'provider-1',
      providerType: 'openai_compatible',
      displayName: 'Local relay',
      baseUrl: 'https://relay.example/v1',
      authType: 'api_key_bearer',
      apiKeyId: 'key-1',
      defaultModel: 'gpt-4o-mini',
      capabilities: {
        ...DEFAULT_PROVIDER_CAPABILITIES,
        chat: true,
      },
      timeoutSeconds: 60,
      rateLimitPolicy: {},
      streamingEnabled: false,
      toolCallingEnabled: false,
      isActive: true,
    })
    expect(JSON.stringify(config)).not.toContain('sk-secret')
  })

  it('maps Provider health and degraded model listing results', () => {
    expect(
      toProviderHealthResult({
        status: 'unhealthy',
        errorCode: 'provider_auth_failed',
        errorMessage: 'Provider authentication failed.',
        modelTested: 'gpt-test',
      }),
    ).toMatchObject({
      status: 'unhealthy',
      errorCode: 'provider_auth_failed',
      modelTested: 'gpt-test',
    })

    expect(
      toProviderModelsResult({
        status: 'degraded',
        models: [],
        manualEntryAllowed: true,
        error: {
          code: 'provider_auth_failed',
          message: 'Provider authentication failed.',
          retryable: false,
          details: {},
        },
      }),
    ).toMatchObject({
      status: 'degraded',
      models: [],
      manualEntryAllowed: true,
      error: {
        code: 'provider_auth_failed',
      },
    })
  })
})

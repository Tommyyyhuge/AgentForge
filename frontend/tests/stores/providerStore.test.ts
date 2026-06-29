import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useProviderStore } from '../../src/stores/providerStore'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('../../src/api/client', () => ({
  default: {
    get: mocks.get,
    post: mocks.post,
    delete: mocks.delete,
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

describe('providerStore API contract', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProviderStore.setState({
      presets: [],
      providers: [],
      modelsByProviderId: {},
      healthByProviderId: {},
      isLoading: false,
      isSaving: false,
      testingProviderId: null,
      error: null,
      validationError: null,
    })
  })

  it('loads Provider presets and configs through standard envelopes', async () => {
    mocks.get
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: [
            {
              providerType: 'openai_compatible',
              displayName: 'OpenAI-compatible relay',
              implementationStatus: 'implemented',
              authType: 'api_key_bearer',
              capabilities: { chat: true },
              isRelay: true,
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: [
            {
              id: 'provider-1',
              providerType: 'openai_compatible',
              displayName: 'Local relay',
              baseUrl: 'https://relay.example/v1',
              authType: 'api_key_bearer',
              defaultModel: 'gpt-4o-mini',
              capabilities: { chat: true },
              timeoutSeconds: 60,
              rateLimitPolicy: {},
              streamingEnabled: false,
              toolCallingEnabled: false,
              isActive: true,
            },
          ],
        },
      })

    await useProviderStore.getState().fetchProviderSettings()

    expect(mocks.get).toHaveBeenNthCalledWith(1, '/providers/presets')
    expect(mocks.get).toHaveBeenNthCalledWith(2, '/providers')
    expect(useProviderStore.getState().presets[0].providerType).toBe('openai_compatible')
    expect(useProviderStore.getState().providers[0].displayName).toBe('Local relay')
  })

  it('creates a relay Provider through API Key and Provider config APIs', async () => {
    mocks.post
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
            id: 'key-1',
            provider: 'openai_compatible',
            masked_key: 'sk-r****1234',
            permission: 'write',
          },
        },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
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
          },
        },
      })

    await useProviderStore.getState().createRelayProvider({
      displayName: 'Local relay',
      baseUrl: 'https://relay.example/v1',
      apiKey: 'sk-real-secret',
      defaultModel: 'gpt-4o-mini',
      streamingEnabled: false,
      toolCallingEnabled: false,
    })

    expect(mocks.post).toHaveBeenNthCalledWith(1, '/keys', {
      provider: 'openai_compatible',
      api_key: 'sk-real-secret',
      permission: 'write',
    })
    expect(mocks.post).toHaveBeenNthCalledWith(2, '/providers', expect.objectContaining({
      apiKeyId: 'key-1',
      providerType: 'openai_compatible',
      displayName: 'Local relay',
    }))
    expect(useProviderStore.getState().providers[0].apiKeyId).toBe('key-1')
    expect(JSON.stringify(useProviderStore.getState())).not.toContain('sk-real-secret')
  })

  it('creates an official Provider from a preset without storing plaintext key', async () => {
    mocks.post
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
            id: 'key-openai',
            provider: 'openai',
            masked_key: 'sk-o****1234',
            permission: 'write',
          },
        },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
            id: 'provider-openai',
            providerType: 'openai',
            displayName: 'OpenAI',
            baseUrl: 'https://api.openai.com/v1',
            authType: 'api_key_bearer',
            apiKeyId: 'key-openai',
            defaultModel: 'gpt-4o-mini',
            capabilities: { chat: true, streaming: true, model_listing: true },
            timeoutSeconds: 60,
            rateLimitPolicy: {},
            streamingEnabled: true,
            toolCallingEnabled: false,
            isActive: true,
          },
        },
      })

    await useProviderStore.getState().createProviderFromPreset({
      providerType: 'openai',
      displayName: 'OpenAI',
      baseUrl: 'https://api.openai.com/v1',
      apiKey: 'sk-openai-secret',
      defaultModel: 'gpt-4o-mini',
      capabilities: {
        chat: true,
        streaming: true,
        tool_calling: false,
        json_mode: true,
        vision: true,
        embeddings: true,
        model_listing: true,
        usage_reporting: true,
      },
      streamingEnabled: true,
      toolCallingEnabled: false,
    })

    expect(mocks.post).toHaveBeenNthCalledWith(1, '/keys', {
      provider: 'openai',
      api_key: 'sk-openai-secret',
      permission: 'write',
    })
    expect(mocks.post).toHaveBeenNthCalledWith(2, '/providers', expect.objectContaining({
      apiKeyId: 'key-openai',
      providerType: 'openai',
      displayName: 'OpenAI',
      capabilities: expect.objectContaining({
        model_listing: true,
      }),
    }))
    expect(useProviderStore.getState().providers[0].providerType).toBe('openai')
    expect(JSON.stringify(useProviderStore.getState())).not.toContain('sk-openai-secret')
  })

  it('stores Provider test and degraded model listing results', async () => {
    mocks.post.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          status: 'unhealthy',
          errorCode: 'provider_auth_failed',
          errorMessage: 'Provider authentication failed.',
          modelTested: 'gpt-test',
        },
      },
    })
    mocks.get.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          status: 'degraded',
          models: [],
          manualEntryAllowed: true,
          error: {
            code: 'provider_auth_failed',
            message: 'Provider authentication failed.',
            retryable: false,
            details: {},
          },
        },
      },
    })

    await useProviderStore.getState().testProviderConfig('provider-1', 'gpt-test')
    await useProviderStore.getState().loadProviderModels('provider-1')

    expect(useProviderStore.getState().healthByProviderId['provider-1'].status).toBe('unhealthy')
    expect(useProviderStore.getState().modelsByProviderId['provider-1'].status).toBe('degraded')
  })
})

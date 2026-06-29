import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../../src/pages/Settings'

const providerMocks = vi.hoisted(() => ({
  fetchProviderSettings: vi.fn(),
  createRelayProvider: vi.fn(),
  createProviderFromPreset: vi.fn(),
  testProviderConfig: vi.fn(),
  loadProviderModels: vi.fn(),
  deleteProviderConfig: vi.fn(),
  clearError: vi.fn(),
  state: {
    providers: [] as unknown[],
    modelsByProviderId: {} as Record<string, unknown>,
    healthByProviderId: {} as Record<string, unknown>,
  },
}))

vi.mock('../../src/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'user-1', username: 'user', email: 'user@example.com' },
    isAuthenticated: true,
    isLoading: false,
    error: null,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    clearError: vi.fn(),
  }),
}))

vi.mock('../../src/hooks/useTheme', () => ({
  useTheme: () => ({
    theme: 'dark',
    setTheme: vi.fn(),
  }),
}))

vi.mock('../../src/stores/providerStore', () => ({
  useProviderStore: () => ({
    presets: [
      {
        providerType: 'openai',
        displayName: 'OpenAI',
        baseUrl: 'https://api.openai.com/v1',
        defaultModel: 'gpt-4o-mini',
        implementationStatus: 'implemented',
        authType: 'api_key_bearer',
        capabilities: {
          chat: true,
          streaming: true,
          tool_calling: true,
          json_mode: true,
          vision: true,
          embeddings: true,
          model_listing: true,
          usage_reporting: true,
        },
        aliases: [],
        isRelay: false,
      },
      {
        providerType: 'openai_compatible',
        displayName: 'OpenAI-compatible relay',
        implementationStatus: 'implemented',
        authType: 'api_key_bearer',
        capabilities: { chat: true },
        isRelay: true,
      },
    ],
    providers: providerMocks.state.providers,
    modelsByProviderId: providerMocks.state.modelsByProviderId,
    healthByProviderId: providerMocks.state.healthByProviderId,
    isLoading: false,
    isSaving: false,
    testingProviderId: null,
    error: null,
    validationError: null,
    ...providerMocks,
  }),
}))

describe('Settings Provider section', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    providerMocks.state.providers = []
    providerMocks.state.modelsByProviderId = {}
    providerMocks.state.healthByProviderId = {}
  })

  it('renders Provider configuration empty state and relay form', async () => {
    render(<Settings />)

    expect(providerMocks.fetchProviderSettings).toHaveBeenCalled()
    expect(screen.getByText('Provider Configuration')).toBeInTheDocument()
    expect(screen.getByText('No Provider configs yet.')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Display name'), 'Local relay')
    await userEvent.type(screen.getByLabelText('Base URL'), 'https://relay.example/v1')
    await userEvent.type(screen.getByLabelText('API Key'), 'sk-real-secret')
    await userEvent.type(screen.getByLabelText('Default model'), 'gpt-4o-mini')
    await userEvent.click(screen.getByRole('button', { name: 'Save Provider' }))

    expect(providerMocks.createRelayProvider).toHaveBeenCalledWith(expect.objectContaining({
      displayName: 'Local relay',
      baseUrl: 'https://relay.example/v1',
      defaultModel: 'gpt-4o-mini',
    }))
  })

  it('creates an official Provider from a preset selection', async () => {
    vi.mocked(providerMocks.createRelayProvider).mockClear()
    render(<Settings />)

    await userEvent.selectOptions(screen.getByLabelText('Provider type'), 'openai')
    await userEvent.type(screen.getByLabelText('API Key'), 'sk-openai-secret')
    await userEvent.click(screen.getByRole('button', { name: 'Save Provider' }))

    expect(providerMocks.createProviderFromPreset).toHaveBeenCalledWith(expect.objectContaining({
      providerType: 'openai',
      displayName: 'OpenAI',
      defaultModel: 'gpt-4o-mini',
    }))
    expect(providerMocks.createRelayProvider).not.toHaveBeenCalled()
  })

  it('uses a selected listed model when testing a Provider', async () => {
    providerMocks.state.providers = [
      {
        id: 'provider-openai',
        providerType: 'openai',
        displayName: 'OpenAI',
        baseUrl: 'https://api.openai.com/v1',
        authType: 'api_key_bearer',
        apiKeyId: 'key-openai',
        defaultModel: 'gpt-4o-mini',
        capabilities: { chat: true, model_listing: true },
        timeoutSeconds: 60,
        rateLimitPolicy: {},
        streamingEnabled: true,
        toolCallingEnabled: true,
        isActive: true,
      },
    ]
    providerMocks.state.modelsByProviderId = {
      'provider-openai': {
        status: 'available',
        models: [
          { id: 'gpt-4o-mini', displayName: 'GPT-4o mini' },
          { id: 'gpt-4o', displayName: 'GPT-4o' },
        ],
        manualEntryAllowed: true,
        error: null,
      },
    }

    render(<Settings />)

    await userEvent.selectOptions(screen.getByLabelText('Model for OpenAI'), 'gpt-4o')
    await userEvent.click(screen.getByRole('button', { name: 'Test Provider' }))

    expect(providerMocks.testProviderConfig).toHaveBeenCalledWith('provider-openai', 'gpt-4o')
  })

  it('uses a manual model when model listing is degraded', async () => {
    providerMocks.state.providers = [
      {
        id: 'provider-relay',
        providerType: 'openai_compatible',
        displayName: 'Local relay',
        baseUrl: 'https://relay.example/v1',
        authType: 'api_key_bearer',
        apiKeyId: 'key-relay',
        defaultModel: 'gpt-4o-mini',
        capabilities: { chat: true },
        timeoutSeconds: 60,
        rateLimitPolicy: {},
        streamingEnabled: false,
        toolCallingEnabled: false,
        isActive: true,
      },
    ]
    providerMocks.state.modelsByProviderId = {
      'provider-relay': {
        status: 'degraded',
        models: [],
        manualEntryAllowed: true,
        error: {
          code: 'provider_model_listing_failed',
          message: 'Provider model listing failed.',
          retryable: true,
          details: {},
        },
      },
    }

    render(<Settings />)

    await userEvent.clear(screen.getByLabelText('Manual model for Local relay'))
    await userEvent.type(screen.getByLabelText('Manual model for Local relay'), 'custom-relay-model')
    await userEvent.click(screen.getByRole('button', { name: 'Test Provider' }))

    expect(screen.getByText('Model listing degraded. Manual model entry is available.')).toBeInTheDocument()
    expect(providerMocks.testProviderConfig).toHaveBeenCalledWith('provider-relay', 'custom-relay-model')
  })
})

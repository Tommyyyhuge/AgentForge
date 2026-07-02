import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../../src/pages/Settings'

const apiKeyMocks = vi.hoisted(() => ({
  fetchApiKeys: vi.fn(),
  createApiKey: vi.fn(),
  deleteApiKey: vi.fn(),
  keys: [
    {
      id: 'key-1',
      provider: 'kimi',
      maskedKey: 'sk-****-1234',
      permission: 'write' as const,
      usageCount: 2,
      isActive: true,
      createdAt: '2026-06-26T01:00:00Z',
    },
  ],
}))

const providerMocks = vi.hoisted(() => ({
  fetchProviderSettings: vi.fn(),
  createRelayProvider: vi.fn(),
  createProviderFromPreset: vi.fn(),
  testProviderConfig: vi.fn(),
  loadProviderModels: vi.fn(),
  deleteProviderConfig: vi.fn(),
  clearError: vi.fn(),
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
    presets: [],
    providers: [],
    modelsByProviderId: {},
    healthByProviderId: {},
    isLoading: false,
    isSaving: false,
    testingProviderId: null,
    error: null,
    validationError: null,
    ...providerMocks,
  }),
}))

vi.mock('../../src/api/apiKeys', () => ({
  fetchApiKeys: apiKeyMocks.fetchApiKeys,
  createApiKey: apiKeyMocks.createApiKey,
  deleteApiKey: apiKeyMocks.deleteApiKey,
  getApiErrorMessage: vi.fn((_error: unknown, fallback = '操作失败') => fallback),
  unwrapApiData: vi.fn((value: unknown) => value),
  toApiKey: vi.fn((value: unknown) => value),
}))

describe('Settings API Key section', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiKeyMocks.fetchApiKeys.mockResolvedValue(apiKeyMocks.keys)
    apiKeyMocks.createApiKey.mockResolvedValue(apiKeyMocks.keys[0])
    apiKeyMocks.deleteApiKey.mockResolvedValue(undefined)
  })

  it('uses typed API helpers and shows safe API Key management copy', async () => {
    render(<Settings />)

    expect(await screen.findByText('Kimi (Moonshot)')).toBeInTheDocument()
    expect(apiKeyMocks.fetchApiKeys).toHaveBeenCalled()
    expect(screen.queryByText(/AES-128-CBC/)).not.toBeInTheDocument()

    const deleteButton = screen.getByRole('button', {
      name: 'Delete API Key for Kimi (Moonshot)',
    })

    await userEvent.click(deleteButton)
    expect(apiKeyMocks.deleteApiKey).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toHaveTextContent('删除 API Key')

    await userEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => {
      expect(apiKeyMocks.deleteApiKey).toHaveBeenCalledWith('key-1')
    })
    expect(screen.queryByText('Kimi (Moonshot)')).not.toBeInTheDocument()
  })
})

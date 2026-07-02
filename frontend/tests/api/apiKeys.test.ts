import { beforeEach, describe, expect, it, vi } from 'vitest'
import apiClient from '../../src/api/client'
import {
  createApiKey,
  deleteApiKey,
  fetchApiKeys,
  toApiKey,
  unwrapApiData,
} from '../../src/api/apiKeys'

vi.mock('../../src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('api key API mapping', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('unwraps standard success envelopes and legacy raw payloads', () => {
    const wrapped = {
      success: true,
      data: [{ id: 'key-1', provider: 'kimi' }],
    } as const
    const raw = [{ id: 'key-2', provider: 'deepseek' }]

    expect(unwrapApiData(wrapped)).toEqual(wrapped.data)
    expect(unwrapApiData(raw)).toEqual(raw)
  })

  it('maps backend API key fields into the frontend domain shape', () => {
    expect(
      toApiKey({
        id: 'key-1',
        provider: 'kimi',
        masked_key: 'sk-****-1234',
        permission: 'write',
        usage_count: 3,
        is_active: true,
        created_at: '2026-06-26T01:00:00Z',
        last_used_at: '2026-06-27T01:00:00Z',
      }),
    ).toEqual({
      id: 'key-1',
      provider: 'kimi',
      maskedKey: 'sk-****-1234',
      permission: 'write',
      usageCount: 3,
      isActive: true,
      createdAt: '2026-06-26T01:00:00Z',
      lastUsedAt: '2026-06-27T01:00:00Z',
    })
  })

  it('fetches API keys through the API boundary and maps the response', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        success: true,
        data: [
          {
            id: 'key-1',
            provider: 'kimi',
            masked_key: 'sk-****-1234',
            permission: 'write',
            usage_count: 2,
            is_active: true,
            created_at: '2026-06-26T01:00:00Z',
          },
        ],
      },
    })

    await expect(fetchApiKeys()).resolves.toEqual([
      expect.objectContaining({
        id: 'key-1',
        provider: 'kimi',
        maskedKey: 'sk-****-1234',
        usageCount: 2,
      }),
    ])
    expect(apiClient.get).toHaveBeenCalledWith('/keys')
  })

  it('creates and deletes API keys through typed API helpers', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          id: 'key-created',
          provider: 'deepseek',
          maskedKey: 'sk-****-5678',
          permission: 'write',
        },
      },
    })
    vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: { success: true, data: null } })

    await expect(
      createApiKey({ provider: 'deepseek', apiKey: 'sk-secret', permission: 'write' }),
    ).resolves.toMatchObject({
      id: 'key-created',
      provider: 'deepseek',
      maskedKey: 'sk-****-5678',
    })
    expect(apiClient.post).toHaveBeenCalledWith('/keys', {
      provider: 'deepseek',
      api_key: 'sk-secret',
      permission: 'write',
    })

    await deleteApiKey('key-created')
    expect(apiClient.delete).toHaveBeenCalledWith('/keys/key-created')
  })
})

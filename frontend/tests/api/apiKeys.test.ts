import { describe, expect, it } from 'vitest'
import { toApiKey, unwrapApiData } from '../../src/api/apiKeys'

describe('api key API mapping', () => {
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
})

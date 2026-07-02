import { describe, expect, it } from 'vitest'
import { getApiErrorMessage, unwrapApiData } from '../../src/api/envelope'

describe('API envelope helpers', () => {
  it('unwraps standard success envelopes', () => {
    const body = {
      success: true,
      data: { id: 'task-1' },
      message: 'Created',
    } as const

    expect(unwrapApiData(body)).toEqual({ id: 'task-1' })
  })

  it('returns legacy raw payloads unchanged', () => {
    const body = [{ id: 'task-1' }]

    expect(unwrapApiData(body)).toBe(body)
  })

  it('extracts safe messages from standard error envelopes', () => {
    const error = {
      response: {
        data: {
          success: false,
          error: {
            code: 'PROVIDER_AUTH_FAILED',
            message: 'Provider authentication failed.',
            details: { provider: 'deepseek' },
          },
        },
      },
    }

    expect(getApiErrorMessage(error)).toBe('Provider authentication failed.')
  })

  it('falls back to Error messages and default text', () => {
    expect(getApiErrorMessage(new Error('Network exploded'))).toBe('Network exploded')
    expect(getApiErrorMessage(undefined)).toBe('操作失败，请稍后重试')
  })
})

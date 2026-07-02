import { describe, expect, it } from 'vitest'
import {
  toAgentMetrics,
  toProviderMetrics,
  toSystemMetrics,
  toTaskDurationMetrics,
  unwrapApiData,
} from '../../src/api/metrics'

describe('metrics API mapping', () => {
  it('unwraps standard success envelopes and legacy raw payloads', () => {
    const wrapped = {
      success: true,
      data: { timestamps: ['10:00'], durations: [120], counts: [3] },
    } as const
    const raw = { timestamps: ['11:00'], durations: [90], counts: [1] }

    expect(unwrapApiData(wrapped)).toEqual(wrapped.data)
    expect(unwrapApiData(raw)).toBe(raw)
  })

  it('maps task metric arrays into chart points', () => {
    expect(
      toTaskDurationMetrics({
        timestamps: ['10:00', '14:00'],
        durations: [120],
        counts: [3, 5],
      }),
    ).toEqual([
      { time: '10:00', duration: 120, count: 3 },
      { time: '14:00', duration: 0, count: 5 },
    ])
  })

  it('keeps agent metrics as typed chart data', () => {
    expect(
      toAgentMetrics([
        { name: 'coder', calls: 4, avgDuration: 320 },
      ]),
    ).toEqual([
      { name: 'coder', calls: 4, avgDuration: 320 },
    ])
  })

  it('normalizes missing system metric fields to safe zeros', () => {
    expect(toSystemMetrics({ cpuUsage: 11.2, activeTasks: 2 })).toEqual({
      cpuUsage: 11.2,
      memoryUsage: 0,
      activeTasks: 2,
      totalRequests: 0,
    })
  })

  it('maps provider metrics and drops unknown sensitive fields', () => {
    const result = toProviderMetrics([
      {
        provider: 'openai',
        model: 'gpt-4o-mini',
        calls: 2,
        failures: 1,
        avgLatencyMs: 180,
        inputTokens: 30,
        outputTokens: 30,
        totalTokens: 60,
        errorCategories: [{ category: 'provider_timeout', count: 1 }],
        apiKey: 'sk-secret',
        prompt: 'private prompt',
      },
    ])

    expect(result).toEqual([
      {
        provider: 'openai',
        model: 'gpt-4o-mini',
        calls: 2,
        failures: 1,
        avgLatencyMs: 180,
        inputTokens: 30,
        outputTokens: 30,
        totalTokens: 60,
        errorCategories: [{ category: 'provider_timeout', count: 1 }],
      },
    ])
    expect(JSON.stringify(result)).not.toContain('sk-secret')
    expect(JSON.stringify(result)).not.toContain('private prompt')
  })
})

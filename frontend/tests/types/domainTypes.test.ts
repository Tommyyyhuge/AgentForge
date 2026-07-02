import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  MEMORY_TYPES,
  PROVIDER_CAPABILITIES,
  PROVIDER_HEALTH_STATUSES,
  PROVIDER_TYPES,
} from '../../src/types'
import type {
  AgentMetric,
  DashboardMetrics,
  Memory,
  MemoryType,
  MetricPoint,
  ModelConfig,
  ProviderCapability,
  ProviderConfig,
  ProviderHealthCheck,
  ProviderHealthStatus,
  ProviderType,
  SystemMetrics,
  TaskDurationMetric,
} from '../../src/types'

describe('domain types', () => {
  it('defines Memory as reusable execution context', () => {
    expectTypeOf<Memory>().toMatchTypeOf<{
      id: string
      content: string
      memoryType: MemoryType
      createdAt: string
    }>()
    expect(MEMORY_TYPES).toEqual(['long_term', 'external'])
  })

  it('defines Provider and model configuration contracts', () => {
    expectTypeOf<ProviderConfig>().toMatchTypeOf<{
      id: string
      providerType: ProviderType
      displayName: string
      capabilities: Record<ProviderCapability, boolean>
      isActive: boolean
    }>()
    expectTypeOf<ModelConfig>().toMatchTypeOf<{
      providerId: string
      modelId: string
    }>()
    expectTypeOf<ProviderHealthCheck>().toMatchTypeOf<{
      status: ProviderHealthStatus
      checkedAt: string
    }>()
    expect(PROVIDER_TYPES).toContain('openai_compatible')
    expect(PROVIDER_CAPABILITIES).toEqual([
      'chat',
      'streaming',
      'tool_calling',
      'json_mode',
      'vision',
      'embeddings',
      'model_listing',
      'usage_reporting',
    ])
    expect(PROVIDER_HEALTH_STATUSES).toEqual([
      'unknown',
      'healthy',
      'degraded',
      'unhealthy',
    ])
  })

  it('defines dashboard metric contracts in the shared type layer', () => {
    expectTypeOf<DashboardMetrics>().toEqualTypeOf<{
      taskMetrics: TaskDurationMetric[]
      agentMetrics: AgentMetric[]
      systemMetrics: SystemMetrics
    }>()
    expectTypeOf<MetricPoint>().toMatchTypeOf<{
      time: string
      value: number
    }>()
  })
})

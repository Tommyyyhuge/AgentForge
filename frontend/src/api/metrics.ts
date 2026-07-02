import apiClient from './client'
import { unwrapApiData } from './envelope'
import type {
  AgentMetric,
  ApiResponse,
  DashboardMetrics,
  ProviderMetric,
  SystemMetrics,
  TaskDurationMetric,
  TaskMetricsPayload,
} from '../types'

export { unwrapApiData }
export type {
  AgentMetric,
  DashboardMetrics,
  ProviderMetric,
  SystemMetrics,
  TaskDurationMetric,
  TaskMetricsPayload,
} from '../types'

export function toTaskDurationMetrics(
  payload: TaskMetricsPayload,
): TaskDurationMetric[] {
  const timestamps = Array.isArray(payload.timestamps) ? payload.timestamps : []
  const durations = Array.isArray(payload.durations) ? payload.durations : []
  const counts = Array.isArray(payload.counts) ? payload.counts : []

  return timestamps.map((time, index) => ({
    time,
    duration: durations[index] ?? 0,
    count: counts[index] ?? 0,
  }))
}

export function toAgentMetrics(payload: unknown): AgentMetric[] {
  if (!Array.isArray(payload)) {
    return []
  }

  return payload.map((item) => {
    const record = item as Partial<AgentMetric>
    return {
      name: typeof record.name === 'string' ? record.name : '',
      calls: typeof record.calls === 'number' ? record.calls : 0,
      avgDuration:
        typeof record.avgDuration === 'number' ? record.avgDuration : 0,
    }
  })
}

export function toProviderMetrics(payload: unknown): ProviderMetric[] {
  if (!Array.isArray(payload)) {
    return []
  }

  return payload.map((item) => {
    const record = item as Partial<ProviderMetric>
    const errorCategories = Array.isArray(record.errorCategories)
      ? record.errorCategories.map((category) => ({
          category:
            typeof category.category === 'string' ? category.category : '',
          count: typeof category.count === 'number' ? category.count : 0,
        }))
      : []

    return {
      provider: typeof record.provider === 'string' ? record.provider : '',
      model: typeof record.model === 'string' ? record.model : '',
      calls: typeof record.calls === 'number' ? record.calls : 0,
      failures: typeof record.failures === 'number' ? record.failures : 0,
      avgLatencyMs:
        typeof record.avgLatencyMs === 'number' ? record.avgLatencyMs : 0,
      inputTokens:
        typeof record.inputTokens === 'number' ? record.inputTokens : 0,
      outputTokens:
        typeof record.outputTokens === 'number' ? record.outputTokens : 0,
      totalTokens:
        typeof record.totalTokens === 'number' ? record.totalTokens : 0,
      errorCategories,
    }
  })
}

export function toSystemMetrics(payload: Partial<SystemMetrics>): SystemMetrics {
  return {
    cpuUsage: typeof payload.cpuUsage === 'number' ? payload.cpuUsage : 0,
    memoryUsage:
      typeof payload.memoryUsage === 'number' ? payload.memoryUsage : 0,
    activeTasks:
      typeof payload.activeTasks === 'number' ? payload.activeTasks : 0,
    totalRequests:
      typeof payload.totalRequests === 'number' ? payload.totalRequests : 0,
  }
}

export async function fetchProviderMetrics(
  rangeHours = 24,
): Promise<ProviderMetric[]> {
  const response = await apiClient.get<
    ProviderMetric[] | ApiResponse<ProviderMetric[]>
  >(`/metrics/providers?range_hours=${rangeHours}`)

  return toProviderMetrics(unwrapApiData(response.data))
}

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  const [taskRes, agentRes, sysRes] = await Promise.all([
    apiClient.get<TaskMetricsPayload | ApiResponse<TaskMetricsPayload>>(
      '/metrics/tasks?range_hours=24',
    ),
    apiClient.get<AgentMetric[] | ApiResponse<AgentMetric[]>>('/metrics/agents'),
    apiClient.get<SystemMetrics | ApiResponse<SystemMetrics>>('/metrics/system'),
  ])

  return {
    taskMetrics: toTaskDurationMetrics(unwrapApiData(taskRes.data)),
    agentMetrics: toAgentMetrics(unwrapApiData(agentRes.data)),
    systemMetrics: toSystemMetrics(unwrapApiData(sysRes.data)),
  }
}

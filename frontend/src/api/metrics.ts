import apiClient from './client'
import { unwrapApiData } from './envelope'
import type {
  AgentMetric,
  ApiResponse,
  DashboardMetrics,
  SystemMetrics,
  TaskDurationMetric,
  TaskMetricsPayload,
} from '../types'

export { unwrapApiData }
export type {
  AgentMetric,
  DashboardMetrics,
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

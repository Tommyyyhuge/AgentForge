import { unwrapApiData } from './envelope'
import type { StepType, Task, TaskPriority, TaskStatus, TaskStep } from '../types'

type RawRecord = Record<string, unknown>

export type TaskPayload = RawRecord
export type TaskStepPayload = RawRecord
export { unwrapApiData }

function asRecord(value: unknown): RawRecord {
  return value && typeof value === 'object' ? value as RawRecord : {}
}

function pickString(record: RawRecord, keys: string[], fallback = ''): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string') return value
  }
  return fallback
}

function pickStringArray(record: RawRecord, keys: string[]): string[] {
  for (const key of keys) {
    const value = record[key]
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string')
    }
  }
  return []
}

export function toTaskStatus(value: unknown): TaskStatus {
  if (
    value === 'planning' ||
    value === 'executing' ||
    value === 'completed' ||
    value === 'failed' ||
    value === 'cancelled' ||
    value === 'pending'
  ) {
    return value
  }
  if (value === 'running') return 'executing'
  return 'pending'
}

function toTaskPriority(value: unknown): TaskPriority {
  if (value === 'low' || value === 'high' || value === 'critical') return value
  return 'medium'
}

export function toTask(input: TaskPayload | unknown): Task {
  const record = asRecord(input)
  const createdAt = pickString(record, ['createdAt', 'created_at'], new Date().toISOString())
  const updatedAt = pickString(record, ['updatedAt', 'updated_at'], createdAt)

  return {
    id: pickString(record, ['id']),
    title: pickString(record, ['title'], '新任务'),
    description: pickString(record, ['description']),
    status: toTaskStatus(record.status),
    priority: toTaskPriority(record.priority),
    assignedAgents: pickStringArray(record, ['assignedAgents', 'assigned_agents']),
    parentId: pickString(record, ['parentId', 'parent_id']) || undefined,
    dependencies: pickStringArray(record, ['dependencies']),
    result: pickString(record, ['result', 'output']) || undefined,
    error: pickString(record, ['error', 'error_message']) || undefined,
    createdAt,
    updatedAt,
    completedAt: pickString(record, ['completedAt', 'completed_at']) || undefined,
  }
}

function toStepType(value: unknown): StepType {
  if (
    value === 'thought' ||
    value === 'action' ||
    value === 'observation' ||
    value === 'final' ||
    value === 'error'
  ) {
    return value
  }
  return 'action'
}

function toStepStatus(value: unknown, stepType: StepType): TaskStep['status'] {
  if (
    value === 'pending' ||
    value === 'running' ||
    value === 'completed' ||
    value === 'failed'
  ) {
    return value
  }
  return stepType === 'error' ? 'failed' : 'completed'
}

export function toTaskStep(input: TaskStepPayload | unknown): TaskStep {
  const record = asRecord(input)
  const stepType = toStepType(record.stepType ?? record.step_type)
  const timestamp = pickString(record, ['startedAt', 'timestamp'])

  return {
    id: pickString(record, ['id']),
    taskId: pickString(record, ['taskId', 'task_id']),
    order: typeof record.order === 'number'
      ? record.order
      : typeof record.step_number === 'number'
        ? record.step_number
        : 0,
    action: pickString(record, ['action', 'content']),
    stepType,
    status: toStepStatus(record.status, stepType),
    result: pickString(record, ['result', 'tool_output']) || undefined,
    agentId: pickString(record, ['agentId', 'agent_id']) || undefined,
    startedAt: timestamp || undefined,
    completedAt: pickString(record, ['completedAt', 'completed_at']) || undefined,
  }
}

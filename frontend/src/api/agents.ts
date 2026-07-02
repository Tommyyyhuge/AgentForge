import { unwrapApiData } from './envelope'
import type { Agent, AgentRole, AgentStatus } from '../types'

type RawRecord = Record<string, unknown>

export type AgentPayload = RawRecord
export { unwrapApiData }

const ROLE_LABELS: Record<AgentRole, string> = {
  researcher: '研究者',
  coder: '程序员',
  writer: '撰写者',
  reviewer: '审查者',
  executor: '执行者',
}

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

export function toAgentRole(value: unknown): AgentRole {
  if (
    value === 'researcher' ||
    value === 'coder' ||
    value === 'writer' ||
    value === 'reviewer' ||
    value === 'executor'
  ) {
    return value
  }
  return 'executor'
}

export function toAgentStatus(value: unknown): AgentStatus {
  if (value === 'error') return 'error'
  if (value === 'busy' || value === 'executing' || value === 'thinking') return 'busy'
  return 'idle'
}

export function toAgent(input: AgentPayload | unknown): Agent {
  const record = asRecord(input)
  const role = toAgentRole(record.role)
  const createdAt = pickString(record, ['createdAt', 'created_at'], new Date().toISOString())
  const updatedAt = pickString(record, ['updatedAt', 'updated_at'], createdAt)
  const name = pickString(record, ['name'], ROLE_LABELS[role])

  return {
    id: pickString(record, ['id'], `agent-${role}`),
    name,
    role,
    status: toAgentStatus(record.status),
    description: pickString(record, ['description'], `${name} agent`),
    model: pickString(record, ['model'], 'configured-llm'),
    createdAt,
    updatedAt,
  }
}

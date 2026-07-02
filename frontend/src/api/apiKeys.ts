import apiClient from './client'
import { getApiErrorMessage, unwrapApiData } from './envelope'
import type { ApiKey, ApiKeyPermission, ApiResponse } from '../types'

type RawRecord = Record<string, unknown>
export { unwrapApiData }

export interface ApiKeyPayload {
  id: string
  provider: string
  masked_key?: string
  maskedKey?: string
  permission?: string
  usage_count?: number
  usageCount?: number
  is_active?: boolean
  isActive?: boolean
  created_at?: string
  createdAt?: string
  last_used_at?: string | null
  lastUsedAt?: string | null
}

export interface CreateApiKeyInput {
  provider: string
  apiKey: string
  permission?: ApiKeyPermission
}

function asRecord(value: unknown): RawRecord {
  return value && typeof value === 'object' ? value as RawRecord : {}
}

function readString(record: RawRecord, keys: string[], fallback = ''): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string') return value
  }
  return fallback
}

function readNumber(record: RawRecord, keys: string[], fallback = 0): number {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number') return value
  }
  return fallback
}

function readBoolean(record: RawRecord, keys: string[], fallback = true): boolean {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'boolean') return value
  }
  return fallback
}

function normalizePermission(value: unknown): ApiKeyPermission {
  if (value === 'read' || value === 'admin') return value
  return 'write'
}

export function toApiKey(payload: ApiKeyPayload | unknown): ApiKey {
  const record = asRecord(payload)
  const lastUsedAt = readString(record, ['lastUsedAt', 'last_used_at'])

  return {
    id: readString(record, ['id']),
    provider: readString(record, ['provider']),
    maskedKey: readString(record, ['maskedKey', 'masked_key']),
    permission: normalizePermission(record.permission),
    usageCount: readNumber(record, ['usageCount', 'usage_count']),
    isActive: readBoolean(record, ['isActive', 'is_active']),
    createdAt: readString(record, ['createdAt', 'created_at']),
    lastUsedAt: lastUsedAt || undefined,
  }
}

export async function fetchApiKeys(): Promise<ApiKey[]> {
  const response = await apiClient.get<ApiResponse<ApiKeyPayload[]> | ApiKeyPayload[]>('/keys')
  return unwrapApiData(response.data).map(toApiKey)
}

export async function createApiKey(input: CreateApiKeyInput): Promise<ApiKey> {
  const response = await apiClient.post<ApiResponse<ApiKeyPayload> | ApiKeyPayload>('/keys', {
    provider: input.provider,
    api_key: input.apiKey,
    permission: input.permission ?? 'write',
  })
  return toApiKey(unwrapApiData(response.data))
}

export async function deleteApiKey(id: string): Promise<void> {
  await apiClient.delete(`/keys/${id}`)
}

export { getApiErrorMessage }

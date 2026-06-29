import apiClient from './client'
import { getApiErrorMessage, unwrapApiData } from './envelope'
import { toApiKey } from './apiKeys'
import type {
  ApiKey,
  ApiResponse,
  CreateProviderConfigInput,
  ProviderAuthType,
  ProviderCapabilities,
  ProviderConfig,
  ProviderErrorSummary,
  ProviderHealthResult,
  ProviderHealthStatus,
  ProviderImplementationStatus,
  ProviderModel,
  ProviderModelsResult,
  ProviderPreset,
  ProviderType,
} from '../types'

type RawRecord = Record<string, unknown>

export const DEFAULT_PROVIDER_CAPABILITIES: ProviderCapabilities = {
  chat: false,
  streaming: false,
  tool_calling: false,
  json_mode: false,
  vision: false,
  embeddings: false,
  model_listing: false,
  usage_reporting: false,
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

function readOptionalString(record: RawRecord, keys: string[]): string | undefined {
  const value = readString(record, keys)
  return value || undefined
}

function readNumber(record: RawRecord, keys: string[], fallback: number): number {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number') return value
  }
  return fallback
}

function readBoolean(record: RawRecord, keys: string[], fallback: boolean): boolean {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'boolean') return value
  }
  return fallback
}

function readStringArray(record: RawRecord, keys: string[]): string[] {
  for (const key of keys) {
    const value = record[key]
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string')
    }
  }
  return []
}

function toProviderType(value: unknown): ProviderType {
  const providerTypes: ProviderType[] = [
    'openai',
    'anthropic',
    'gemini',
    'deepseek',
    'moonshot',
    'dashscope',
    'zhipu',
    'qianfan',
    'hunyuan',
    'minimax',
    'openai_compatible',
  ]
  return providerTypes.includes(value as ProviderType)
    ? value as ProviderType
    : 'openai_compatible'
}

function toAuthType(value: unknown): ProviderAuthType {
  if (value === 'api_key_header' || value === 'none') return value
  return 'api_key_bearer'
}

function toImplementationStatus(value: unknown): ProviderImplementationStatus {
  return value === 'planned' ? 'planned' : 'implemented'
}

function toHealthStatus(value: unknown): ProviderHealthStatus {
  if (value === 'healthy' || value === 'degraded' || value === 'unhealthy') return value
  return 'unknown'
}

export function toProviderCapabilities(value: unknown): ProviderCapabilities {
  const record = asRecord(value)
  return {
    ...DEFAULT_PROVIDER_CAPABILITIES,
    chat: readBoolean(record, ['chat'], false),
    streaming: readBoolean(record, ['streaming'], false),
    tool_calling: readBoolean(record, ['tool_calling', 'toolCalling'], false),
    json_mode: readBoolean(record, ['json_mode', 'jsonMode'], false),
    vision: readBoolean(record, ['vision'], false),
    embeddings: readBoolean(record, ['embeddings'], false),
    model_listing: readBoolean(record, ['model_listing', 'modelListing'], false),
    usage_reporting: readBoolean(record, ['usage_reporting', 'usageReporting'], false),
  }
}

export function toProviderPreset(payload: unknown): ProviderPreset {
  const record = asRecord(payload)
  return {
    providerType: toProviderType(readString(record, ['providerType', 'provider_type'])),
    displayName: readString(record, ['displayName', 'display_name']),
    baseUrl: readOptionalString(record, ['baseUrl', 'base_url']),
    defaultModel: readOptionalString(record, ['defaultModel', 'default_model']),
    implementationStatus: toImplementationStatus(record.implementationStatus ?? record.implementation_status),
    officialDocsUrl: readOptionalString(record, ['officialDocsUrl', 'official_docs_url']),
    authType: toAuthType(record.authType ?? record.auth_type),
    capabilities: toProviderCapabilities(record.capabilities),
    aliases: readStringArray(record, ['aliases']),
    isRelay: readBoolean(record, ['isRelay', 'is_relay'], false),
  }
}

export function toProviderConfig(payload: unknown): ProviderConfig {
  const record = asRecord(payload)
  return {
    id: readString(record, ['id']),
    providerType: toProviderType(readString(record, ['providerType', 'provider_type'])),
    displayName: readString(record, ['displayName', 'display_name']),
    baseUrl: readOptionalString(record, ['baseUrl', 'base_url']),
    authType: toAuthType(record.authType ?? record.auth_type),
    apiKeyId: readOptionalString(record, ['apiKeyId', 'api_key_id']),
    defaultModel: readOptionalString(record, ['defaultModel', 'default_model']),
    capabilities: toProviderCapabilities(record.capabilities),
    timeoutSeconds: readNumber(record, ['timeoutSeconds', 'timeout_seconds'], 60),
    rateLimitPolicy: asRecord(record.rateLimitPolicy ?? record.rate_limit_policy),
    streamingEnabled: readBoolean(record, ['streamingEnabled', 'streaming_enabled'], false),
    toolCallingEnabled: readBoolean(record, ['toolCallingEnabled', 'tool_calling_enabled'], false),
    isActive: readBoolean(record, ['isActive', 'is_active'], true),
    createdAt: readOptionalString(record, ['createdAt', 'created_at']),
    updatedAt: readOptionalString(record, ['updatedAt', 'updated_at']),
  }
}

export function toProviderHealthResult(payload: unknown): ProviderHealthResult {
  const record = asRecord(payload)
  return {
    status: toHealthStatus(record.status),
    latencyMs: readNumber(record, ['latencyMs', 'latency_ms'], 0) || undefined,
    errorCode: readOptionalString(record, ['errorCode', 'error_code']),
    errorMessage: readOptionalString(record, ['errorMessage', 'error_message']),
    modelTested: readOptionalString(record, ['modelTested', 'model_tested']),
  }
}

function toProviderModel(payload: unknown): ProviderModel {
  const record = asRecord(payload)
  return {
    id: readString(record, ['id']),
    displayName: readOptionalString(record, ['displayName', 'display_name']),
  }
}

function toProviderErrorSummary(payload: unknown): ProviderErrorSummary | null {
  const record = asRecord(payload)
  const code = readString(record, ['code'])
  if (!code) return null
  return {
    code,
    message: readString(record, ['message']),
    retryable: readBoolean(record, ['retryable'], false),
    details: asRecord(record.details),
  }
}

export function toProviderModelsResult(payload: unknown): ProviderModelsResult {
  const record = asRecord(payload)
  const models = Array.isArray(record.models) ? record.models.map(toProviderModel) : []
  return {
    status: record.status === 'degraded' ? 'degraded' : 'available',
    models,
    manualEntryAllowed: readBoolean(record, ['manualEntryAllowed', 'manual_entry_allowed'], true),
    error: toProviderErrorSummary(record.error),
  }
}

export async function fetchProviderPresets(): Promise<ProviderPreset[]> {
  const response = await apiClient.get<ApiResponse<unknown[]> | unknown[]>('/providers/presets')
  return unwrapApiData(response.data).map(toProviderPreset)
}

export async function fetchProviderConfigs(): Promise<ProviderConfig[]> {
  const response = await apiClient.get<ApiResponse<unknown[]> | unknown[]>('/providers')
  return unwrapApiData(response.data).map(toProviderConfig)
}

export async function createApiKeyForProvider(
  provider: ProviderType,
  apiKey: string,
): Promise<ApiKey> {
  const response = await apiClient.post('/keys', {
    provider,
    api_key: apiKey,
    permission: 'write',
  })
  return toApiKey(unwrapApiData(response.data))
}

export async function createProviderConfig(
  input: CreateProviderConfigInput,
): Promise<ProviderConfig> {
  const response = await apiClient.post('/providers', {
    providerType: input.providerType,
    displayName: input.displayName,
    baseUrl: input.baseUrl || undefined,
    authType: 'api_key_bearer',
    apiKeyId: input.apiKeyId,
    defaultModel: input.defaultModel || undefined,
    capabilities: {
      ...DEFAULT_PROVIDER_CAPABILITIES,
      ...input.capabilities,
    },
    timeoutSeconds: input.timeoutSeconds ?? 60,
    rateLimitPolicy: {},
    streamingEnabled: input.streamingEnabled,
    toolCallingEnabled: input.toolCallingEnabled,
  })
  return toProviderConfig(unwrapApiData(response.data))
}

export async function testProviderConfig(
  providerId: string,
  modelId?: string,
): Promise<ProviderHealthResult> {
  const response = await apiClient.post(`/providers/${providerId}/test`, {
    modelId: modelId || undefined,
  })
  return toProviderHealthResult(unwrapApiData(response.data))
}

export async function fetchProviderModels(providerId: string): Promise<ProviderModelsResult> {
  const response = await apiClient.get(`/providers/${providerId}/models`)
  return toProviderModelsResult(unwrapApiData(response.data))
}

export async function deleteProviderConfig(providerId: string): Promise<void> {
  await apiClient.delete(`/providers/${providerId}`)
}

export { getApiErrorMessage }

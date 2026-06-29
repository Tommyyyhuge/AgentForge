// ===== AgentForge 全局类型定义 =====

// ---------- API 响应 ----------
/** 标准 API 成功响应 */
export interface ApiResponse<T = unknown> {
  success: true
  data: T
  message?: string
}

/** 标准 API 错误响应 */
export interface ApiError {
  success: false
  error: {
    code: string
    message: string
    details?: unknown
  }
}

/** 分页参数 */
export interface PaginationParams {
  page: number
  pageSize: number
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// ---------- Agent 核心类型 ----------
/** Agent 角色枚举 */
export type AgentRole =
  | 'researcher'
  | 'coder'
  | 'writer'
  | 'reviewer'
  | 'executor'

/** Agent 状态 */
export type AgentStatus =
  | 'idle'
  | 'busy'
  | 'error'

/** Agent 实体 */
export interface Agent {
  id: string
  name: string
  role: AgentRole
  status: AgentStatus
  description: string
  model: string
  createdAt: string
  updatedAt: string
}

/** Agent 消息 */
export interface AgentMessage {
  id: string
  agentId: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

// ---------- 用户与 API Key 类型 ----------
/** 认证用户 */
export interface User {
  id: string
  username: string
  email: string
}

/** API Key 权限 */
export type ApiKeyPermission = 'read' | 'write' | 'admin'

/** API Key 前端领域对象。明文 key 不进入该类型。 */
export interface ApiKey {
  id: string
  provider: string
  maskedKey: string
  permission: ApiKeyPermission
  usageCount: number
  isActive: boolean
  createdAt: string
  lastUsedAt?: string
}

// ---------- Memory types ----------
export type MemoryType = 'long_term' | 'external'

export const MEMORY_TYPES = ['long_term', 'external'] as const

export interface Memory {
  id: string
  content: string
  memoryType: MemoryType
  agentId?: string
  agentRole?: AgentRole
  taskId?: string
  source?: string
  metadata: Record<string, unknown>
  createdAt: string
}

// ---------- Provider types ----------
export type ProviderType =
  | 'openai'
  | 'anthropic'
  | 'gemini'
  | 'deepseek'
  | 'moonshot'
  | 'dashscope'
  | 'zhipu'
  | 'qianfan'
  | 'hunyuan'
  | 'minimax'
  | 'openai_compatible'

export const PROVIDER_TYPES = [
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
] as const

export type ProviderAuthType = 'api_key_bearer' | 'api_key_header' | 'none'

export type ProviderCapability =
  | 'chat'
  | 'streaming'
  | 'tool_calling'
  | 'json_mode'
  | 'vision'
  | 'embeddings'
  | 'model_listing'
  | 'usage_reporting'

export const PROVIDER_CAPABILITIES = [
  'chat',
  'streaming',
  'tool_calling',
  'json_mode',
  'vision',
  'embeddings',
  'model_listing',
  'usage_reporting',
] as const

export type ProviderCapabilities = Record<ProviderCapability, boolean>

export type ProviderHealthStatus =
  | 'unknown'
  | 'healthy'
  | 'degraded'
  | 'unhealthy'

export const PROVIDER_HEALTH_STATUSES = [
  'unknown',
  'healthy',
  'degraded',
  'unhealthy',
] as const

export interface ProviderConfig {
  id: string
  providerType: ProviderType
  displayName: string
  baseUrl?: string
  authType: ProviderAuthType
  apiKeyId?: string
  defaultModel?: string
  capabilities: ProviderCapabilities
  timeoutSeconds: number
  rateLimitPolicy: Record<string, unknown>
  streamingEnabled: boolean
  toolCallingEnabled: boolean
  isActive: boolean
  createdAt?: string
  updatedAt?: string
}

export type ProviderImplementationStatus = 'implemented' | 'planned'

export interface ProviderPreset {
  providerType: ProviderType
  displayName: string
  baseUrl?: string
  defaultModel?: string
  implementationStatus: ProviderImplementationStatus
  officialDocsUrl?: string
  authType: ProviderAuthType
  capabilities: ProviderCapabilities
  aliases: string[]
  isRelay: boolean
}

export interface ProviderModel {
  id: string
  displayName?: string
}

export interface ProviderErrorSummary {
  code: string
  message: string
  retryable: boolean
  details: Record<string, unknown>
}

export interface ProviderHealthResult {
  status: ProviderHealthStatus
  latencyMs?: number
  errorCode?: string
  errorMessage?: string
  modelTested?: string
}

export interface ProviderModelsResult {
  status: 'available' | 'degraded'
  models: ProviderModel[]
  manualEntryAllowed: boolean
  error?: ProviderErrorSummary | null
}

export interface CreateRelayProviderInput {
  displayName: string
  baseUrl: string
  apiKey: string
  defaultModel: string
  streamingEnabled: boolean
  toolCallingEnabled: boolean
  timeoutSeconds?: number
}

export interface CreateProviderConfigInput {
  providerType: ProviderType
  displayName: string
  baseUrl?: string
  apiKeyId: string
  defaultModel?: string
  capabilities: ProviderCapabilities
  streamingEnabled: boolean
  toolCallingEnabled: boolean
  timeoutSeconds?: number
}

export interface CreateProviderFromPresetInput {
  providerType: ProviderType
  displayName: string
  baseUrl?: string
  apiKey: string
  defaultModel: string
  capabilities: ProviderCapabilities
  streamingEnabled: boolean
  toolCallingEnabled: boolean
  timeoutSeconds?: number
}

export interface ModelConfig {
  id: string
  providerId: string
  modelId: string
  displayName?: string
  contextWindow?: number
  supportsStreaming?: boolean
  supportsToolCalling?: boolean
  supportsJsonMode?: boolean
  supportsVision?: boolean
  supportsEmbeddings?: boolean
  isDefault: boolean
  isActive: boolean
}

export interface ProviderHealthCheck {
  id: string
  providerId: string
  status: ProviderHealthStatus
  checkedAt: string
  latencyMs?: number
  errorCode?: string
  errorMessage?: string
  modelTested?: string
}

// ---------- 任务类型 ----------
/** 任务状态 */
export type TaskStatus =
  | 'pending'
  | 'planning'
  | 'executing'
  | 'completed'
  | 'failed'
  | 'cancelled'

/** 任务优先级 */
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'

/** Step 类型 */
export type StepType = 'thought' | 'action' | 'observation' | 'final' | 'error'

/** 任务实体 */
export interface Task {
  id: string
  title: string
  description: string
  status: TaskStatus
  priority: TaskPriority
  assignedAgents: string[]
  parentId?: string
  dependencies: string[]
  result?: string
  error?: string
  createdAt: string
  updatedAt: string
  completedAt?: string
}

/** 任务执行步骤 */
export interface TaskStep {
  id: string
  taskId: string
  order: number
  action: string
  stepType: StepType
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: string
  agentId?: string
  startedAt?: string
  completedAt?: string
}

// ---------- Metrics types ----------
export interface MetricPoint {
  time: string
  value: number
  label?: string
}

export interface TaskMetricsPayload {
  timestamps?: string[]
  durations?: number[]
  counts?: number[]
}

export interface TaskDurationMetric {
  time: string
  duration: number
  count: number
}

export interface AgentMetric {
  name: string
  calls: number
  avgDuration: number
}

export interface SystemMetrics {
  cpuUsage: number
  memoryUsage: number
  activeTasks: number
  totalRequests: number
}

export interface DashboardMetrics {
  taskMetrics: TaskDurationMetric[]
  agentMetrics: AgentMetric[]
  systemMetrics: SystemMetrics
}

// ---------- 工具/协议类型 ----------
/** MCP 工具定义 */
export interface MCPTool {
  name: string
  description: string
  parameters: Record<string, unknown>
  enabled: boolean
}

/** MCP 工具调用 */
export interface MCPToolCall {
  id: string
  toolName: string
  arguments: Record<string, unknown>
  result?: string
  status: 'pending' | 'running' | 'completed' | 'error'
}

// ---------- Store 类型 ----------
/** 全局 Store 状态快照 */
export interface StoreState {
  agents: Agent[]
  tasks: Task[]
  selectedAgentId: string | null
  selectedTaskId: string | null
  isConnected: boolean
  lastError: string | null
}

/** UI 主题 */
export type ThemeMode = 'light' | 'dark' | 'system'

/** UI Store */
export interface UIState {
  theme: ThemeMode
  sidebarCollapsed: boolean
  activePanel: 'chat' | 'tasks' | 'agents' | 'monitor'
  notifications: UINotification[]
}

/** 通知 */
export interface UINotification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  duration?: number
  timestamp: string
}

// ---------- 通用工具类型 ----------
/** 可空类型 */
export type Nullable<T> = T | null

/** 可选属性 */
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

/** 深度只读 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P]
}

/** 提取数组元素类型 */
export type ArrayElement<T> = T extends readonly (infer E)[] ? E : never

/** 视图模式 */
export type ViewMode = 'grid' | 'list' | 'detail'

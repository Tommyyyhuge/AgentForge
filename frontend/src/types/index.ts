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
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: string
  agentId?: string
  startedAt?: string
  completedAt?: string
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

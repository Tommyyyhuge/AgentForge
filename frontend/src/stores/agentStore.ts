import { create } from 'zustand'
import type { Agent, AgentRole, AgentStatus, ApiResponse } from '../types'
import apiClient, { createSSEConnection } from '../api/client'

// ============================================================
// 状态标签 & 颜色映射（被页面组件直接引用）
// ============================================================

export const AGENT_STATUS_COLORS: Record<AgentStatus, string> = {
  idle:      'bg-slate-500/10 text-slate-400 border-slate-500/20',
  busy:      'bg-amber-500/10 text-amber-400 border-amber-500/20',
  error:     'bg-red-500/10 text-red-400 border-red-500/20',
}

export const AGENT_STATUS_LABELS: Record<AgentStatus, string> = {
  idle:      '空闲',
  busy:      '忙碌',
  error:     '错误',
}

export const AGENT_ROLE_LABELS: Record<AgentRole, string> = {
  researcher:    '研究者',
  coder:         '程序员',
  writer:        '撰写者',
  reviewer:      '审查者',
  executor:      '执行者',
}

// ============================================================
// Mock 数据（API 不可用时的降级方案）
// ============================================================

const MOCK_AGENTS: Agent[] = [
  {
    id: 'agent-1',
    name: 'Researcher',
    role: 'researcher',
    status: 'busy',
    description: '信息搜索、资料整理和事实核查',
    model: 'deepseek-v4-pro',
    createdAt: '2026-05-15T08:00:00Z',
    updatedAt: '2026-05-20T14:00:00Z',
  },
  {
    id: 'agent-2',
    name: 'Coder',
    role: 'coder',
    status: 'idle',
    description: '代码生成、脚本编写和技术实现',
    model: 'deepseek-v4-pro',
    createdAt: '2026-05-15T08:30:00Z',
    updatedAt: '2026-05-20T12:00:00Z',
  },
  {
    id: 'agent-3',
    name: 'Writer',
    role: 'writer',
    status: 'idle',
    description: '结果整合、报告撰写和表达优化',
    model: 'deepseek-v4-pro',
    createdAt: '2026-05-16T09:00:00Z',
    updatedAt: '2026-05-20T10:00:00Z',
  },
  {
    id: 'agent-4',
    name: 'Reviewer',
    role: 'reviewer',
    status: 'idle',
    description: '代码审查与质量把控，确保输出符合规范',
    model: 'deepseek-v4-pro',
    createdAt: '2026-05-16T10:00:00Z',
    updatedAt: '2026-05-20T08:00:00Z',
  },
]

// ============================================================
// 辅助函数
// ============================================================

function extractData<T>(response: { data: ApiResponse<T> | T }): T {
  const body = response.data
  if (
    body &&
    typeof body === 'object' &&
    'success' in body &&
    body.success === true
  ) {
    return body.data
  }
  return body as T
}

function isNetworkError(error: unknown): boolean {
  return error instanceof Error &&
    (error.message.includes('无法连接') || error.message.includes('网络'))
}

type RawRecord = Record<string, unknown>

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

function normalizeAgentRole(value: unknown): AgentRole {
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

function normalizeAgentStatus(value: unknown): AgentStatus {
  if (value === 'error') return 'error'
  if (value === 'busy' || value === 'executing' || value === 'thinking') return 'busy'
  return 'idle'
}

function normalizeAgent(input: unknown): Agent {
  const record = asRecord(input)
  const role = normalizeAgentRole(record.role)
  const createdAt = pickString(record, ['createdAt', 'created_at'], new Date().toISOString())
  const updatedAt = pickString(record, ['updatedAt', 'updated_at'], createdAt)
  const name = pickString(record, ['name'], AGENT_ROLE_LABELS[role])

  return {
    id: pickString(record, ['id'], `agent-${role}`),
    name,
    role,
    status: normalizeAgentStatus(record.status),
    description: pickString(record, ['description'], `${name} agent`),
    model: pickString(record, ['model'], 'configured-llm'),
    createdAt,
    updatedAt,
  }
}

// ============================================================
// Store
// ============================================================

interface AgentStore {
  agents: Agent[]
  isLoading: boolean
  error: string | null

  fetchAgents: () => Promise<void>
  subscribeToAgents: () => () => void   // 返回取消订阅函数
  clearError: () => void
}

export const useAgentStore = create<AgentStore>((set) => ({
  agents: [],
  isLoading: false,
  error: null,

  // ---- 获取 Agent 列表 ----
  fetchAgents: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.get<ApiResponse<unknown[]> | unknown[]>('/agents')
      const agents = extractData<unknown[]>(response).map(normalizeAgent)
      set({ agents, isLoading: false })
    } catch (err) {
      // API 不可达时降级为 mock 数据
      if (isNetworkError(err)) {
        console.warn('[AgentStore] 后端不可达，使用 mock 数据:', (err as Error).message)
        set({ agents: MOCK_AGENTS, isLoading: false })
        return
      }
      set({ isLoading: false, error: (err as Error).message })
    }
  },

  // ---- 订阅 Agent 状态 SSE 流（返回取消订阅函数） ----
  subscribeToAgents: () => {
    let eventSource: EventSource | null = null

    try {
      eventSource = createSSEConnection('/agents/stream', {
        onOpen: () => {
          if (import.meta.env.DEV) {
            console.log('[SSE] 已连接 Agent 状态流')
          }
        },

        onMessage: (data) => {
          // 后端 SSE 推送的数据格式：
          // { type: 'agent_update', agent: Agent }
          const event = data as {
            type: string
            agent?: unknown
          }

          if (event.type === 'agent_update' && event.agent) {
            const nextAgent = normalizeAgent(event.agent)
            set((s) => {
              const idx = s.agents.findIndex((a) => a.id === nextAgent.id)
              if (idx >= 0) {
                const updated = [...s.agents]
                updated[idx] = nextAgent
                return { agents: updated }
              }
              // 新 Agent 出现
              return { agents: [...s.agents, nextAgent] }
            })
          }
        },

        onError: () => {
          // SSE 连接错误，静默处理；数据已通过 fetchAgents 加载
        },
      })
    } catch {
      if (import.meta.env.DEV) {
        console.warn('[SSE] 无法创建 Agent 状态流连接')
      }
    }

    return () => {
      if (eventSource) {
        eventSource.close()
        if (import.meta.env.DEV) {
          console.log('[SSE] 已断开 Agent 状态流')
        }
      }
    }
  },

  clearError: () => set({ error: null }),
}))

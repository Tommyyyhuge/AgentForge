import { create } from 'zustand'
import type { Agent, AgentRole, AgentStatus, ApiResponse } from '../types'
import apiClient, { createSSEConnection } from '../api/client'

// ============================================================
// 状态标签 & 颜色映射（被页面组件直接引用）
// ============================================================

export const AGENT_STATUS_COLORS: Record<AgentStatus, string> = {
  idle:      'bg-slate-500/10 text-slate-400 border-slate-500/20',
  thinking:  'bg-forge-500/10 text-forge-400 border-forge-500/20',
  executing: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  waiting:   'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  error:     'bg-red-500/10 text-red-400 border-red-500/20',
}

export const AGENT_STATUS_LABELS: Record<AgentStatus, string> = {
  idle:      '空闲',
  thinking:  '思考中',
  executing: '执行中',
  waiting:   '等待中',
  completed: '已完成',
  error:     '错误',
}

export const AGENT_ROLE_LABELS: Record<AgentRole, string> = {
  orchestrator:  '调度者',
  analyst:       '分析者',
  executor:      '执行者',
  critic:        '评审者',
  researcher:    '研究者',
  communicator:  '沟通者',
}

// ============================================================
// Mock 数据（API 不可用时的降级方案）
// ============================================================

const MOCK_AGENTS: Agent[] = [
  {
    id: 'agent-1',
    name: 'Prometheus',
    role: 'orchestrator',
    status: 'executing',
    description: '任务调度与编排，拆解复杂需求为可执行子任务',
    model: 'deepseek-v4-pro',
    createdAt: '2026-05-15T08:00:00Z',
    updatedAt: '2026-05-20T14:00:00Z',
  },
  {
    id: 'agent-2',
    name: 'Hephaestus',
    role: 'executor',
    status: 'idle',
    description: '代码生成与文件操作，构建项目骨架',
    model: 'deepseek-v4-pro',
    createdAt: '2026-05-15T08:30:00Z',
    updatedAt: '2026-05-20T12:00:00Z',
  },
  {
    id: 'agent-3',
    name: 'Athena',
    role: 'analyst',
    status: 'thinking',
    description: '需求分析与技术方案评估',
    model: 'deepseek-v4-pro',
    createdAt: '2026-05-16T09:00:00Z',
    updatedAt: '2026-05-20T10:00:00Z',
  },
  {
    id: 'agent-4',
    name: 'Momus',
    role: 'critic',
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

function extractData<T>(response: { data: ApiResponse<T> }): T {
  return response.data.data
}

function isNetworkError(error: unknown): boolean {
  return error instanceof Error &&
    (error.message.includes('无法连接') || error.message.includes('网络'))
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
      const response = await apiClient.get<ApiResponse<Agent[]>>('/agents')
      set({ agents: extractData(response), isLoading: false })
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
            agent?: Agent
          }

          if (event.type === 'agent_update' && event.agent) {
            set((s) => {
              const idx = s.agents.findIndex((a) => a.id === event.agent!.id)
              if (idx >= 0) {
                const updated = [...s.agents]
                updated[idx] = event.agent!
                return { agents: updated }
              }
              // 新 Agent 出现
              return { agents: [...s.agents, event.agent!] }
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

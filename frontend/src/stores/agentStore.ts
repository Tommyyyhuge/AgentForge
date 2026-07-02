import { create } from 'zustand'
import type { Agent, AgentRole, AgentStatus, ApiResponse } from '../types'
import apiClient, { createSSEConnection } from '../api/client'
import { toAgent, unwrapApiData } from '../api/agents'

// ============================================================
// 状态标签 & 颜色映射（被页面组件直接引用）
// ============================================================

export const AGENT_STATUS_COLORS: Record<AgentStatus, string> = {
  idle:      'bg-semantic-idle/10 text-semantic-idle border-semantic-idle/20',
  busy:      'bg-semantic-busy/10 text-semantic-busy border-semantic-busy/20',
  error:     'bg-semantic-error/10 text-semantic-error border-semantic-error/20',
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
      const agents = unwrapApiData(response.data).map(toAgent)
      set({ agents, isLoading: false })
    } catch (err) {
      const message = err instanceof Error ? err.message : '加载 Agent 失败'
      set({ agents: [], isLoading: false, error: message })
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
            const nextAgent = toAgent(event.agent)
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

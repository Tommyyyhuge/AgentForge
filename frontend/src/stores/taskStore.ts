import { create } from 'zustand'
import type { Task, TaskStatus, TaskPriority, ApiResponse } from '../types'
import apiClient, { createSSEConnection } from '../api/client'

// ============================================================
// 展示类型（用于时间线视觉区分）
// ============================================================

export type StepDisplayType = 'thought' | 'action' | 'observation' | 'final'

export interface StepWithDisplay {
  id: string
  taskId: string
  order: number
  action: string
  stepType: StepDisplayType
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: string
  agentId?: string
  startedAt?: string
  completedAt?: string
}

// ============================================================
// 状态标签 & 颜色映射（被页面组件直接引用）
// ============================================================

export const STATUS_COLORS: Record<TaskStatus, string> = {
  pending:   'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  queued:    'bg-blue-500/10 text-blue-400 border-blue-500/20',
  running:   'bg-purple-500/10 text-purple-400 border-purple-500/20',
  paused:    'bg-slate-500/10 text-slate-400 border-slate-500/20',
  completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  failed:    'bg-red-500/10 text-red-400 border-red-500/20',
  cancelled: 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20',
}

export const STATUS_LABELS: Record<TaskStatus, string> = {
  pending:   '待处理',
  queued:    '排队中',
  running:   '进行中',
  paused:    '已暂停',
  completed: '已完成',
  failed:    '失败',
  cancelled: '已取消',
}

export const STEP_TYPE_COLORS: Record<StepDisplayType, string> = {
  thought:     'border-forge-400 bg-forge-500/10 text-forge-300',
  action:      'border-amber-500/30 bg-amber-500/10 text-amber-400',
  observation: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400',
  final:       'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
}

export const STEP_TYPE_LABELS: Record<StepDisplayType, string> = {
  thought:     '思考',
  action:      '行动',
  observation: '观察',
  final:       '完成',
}

// ============================================================
// Mock 数据（API 不可用时的降级方案）
// ============================================================

const MOCK_TASKS: Task[] = [
  {
    id: 'task-1',
    title: '分析用户需求文档',
    description: '读取并分析产品需求文档，提取关键功能点和技术约束',
    status: 'completed',
    priority: 'high' as TaskPriority,
    assignedAgents: ['agent-1'],
    dependencies: [],
    result: '需求分析完成，共提取 12 个功能点',
    createdAt: '2026-05-18T08:00:00Z',
    updatedAt: '2026-05-18T10:30:00Z',
    completedAt: '2026-05-18T10:30:00Z',
  },
  {
    id: 'task-2',
    title: '搭建项目基础架构',
    description: '创建 Vite + React + TypeScript 项目骨架，配置 Tailwind CSS',
    status: 'running',
    priority: 'critical' as TaskPriority,
    assignedAgents: ['agent-1', 'agent-2'],
    dependencies: ['task-1'],
    createdAt: '2026-05-19T09:00:00Z',
    updatedAt: '2026-05-20T14:00:00Z',
  },
  {
    id: 'task-3',
    title: '实现用户认证模块',
    description: '基于 JWT 的用户登录/注册功能',
    status: 'pending',
    priority: 'high' as TaskPriority,
    assignedAgents: ['agent-3'],
    dependencies: ['task-2'],
    createdAt: '2026-05-20T10:00:00Z',
    updatedAt: '2026-05-20T10:00:00Z',
  },
  {
    id: 'task-4',
    title: '设计数据库模型',
    description: '设计 Agent 和 Task 相关的数据库表结构',
    status: 'queued',
    priority: 'medium' as TaskPriority,
    assignedAgents: ['agent-2'],
    dependencies: [],
    createdAt: '2026-05-19T14:00:00Z',
    updatedAt: '2026-05-20T09:00:00Z',
  },
  {
    id: 'task-5',
    title: '编写单元测试',
    description: '为核心业务逻辑编写 Jest 单元测试',
    status: 'failed',
    priority: 'medium' as TaskPriority,
    assignedAgents: ['agent-4'],
    dependencies: ['task-2'],
    error: '测试覆盖率未达到 80% 阈值',
    createdAt: '2026-05-20T08:00:00Z',
    updatedAt: '2026-05-20T12:00:00Z',
  },
  {
    id: 'task-6',
    title: '性能优化 - 前端',
    description: '优化 React 组件渲染性能，减少不必要的 re-render',
    status: 'pending',
    priority: 'low' as TaskPriority,
    assignedAgents: [],
    dependencies: [],
    createdAt: '2026-05-20T11:00:00Z',
    updatedAt: '2026-05-20T11:00:00Z',
  },
]

const MOCK_STEPS: StepWithDisplay[] = [
  {
    id: 'step-1', taskId: 'task-2', order: 1,
    action: '分析当前项目结构，确定最佳目录组织方式',
    stepType: 'thought', status: 'completed',
    agentId: 'agent-1', startedAt: '2026-05-19T09:05:00Z', completedAt: '2026-05-19T09:20:00Z',
  },
  {
    id: 'step-2', taskId: 'task-2', order: 2,
    action: '初始化 Vite 项目并安装依赖',
    stepType: 'action', status: 'completed',
    agentId: 'agent-2', startedAt: '2026-05-19T09:21:00Z', completedAt: '2026-05-19T09:35:00Z',
    result: 'Vite 项目创建成功，所有依赖安装完成',
  },
  {
    id: 'step-3', taskId: 'task-2', order: 3,
    action: '配置 Tailwind CSS 和 PostCSS',
    stepType: 'action', status: 'completed',
    agentId: 'agent-1', startedAt: '2026-05-19T09:36:00Z', completedAt: '2026-05-19T09:50:00Z',
    result: 'Tailwind 配置完成，品牌色系已定义',
  },
  {
    id: 'step-4', taskId: 'task-2', order: 4,
    action: '检查项目文件结构是否符合规范',
    stepType: 'observation', status: 'completed',
    agentId: 'agent-1', startedAt: '2026-05-19T09:51:00Z', completedAt: '2026-05-19T10:00:00Z',
    result: '目录结构符合预期，所有配置文件就位',
  },
  {
    id: 'step-5', taskId: 'task-2', order: 5,
    action: '创建前端布局组件和页面路由',
    stepType: 'action', status: 'running',
    agentId: 'agent-2', startedAt: '2026-05-20T09:00:00Z',
  },
  {
    id: 'step-6', taskId: 'task-2', order: 6,
    action: '最终代码审查和测试',
    stepType: 'final', status: 'pending',
    agentId: 'agent-1',
  },
]

// ============================================================
// API 响应类型（辅助函数内部使用）
// ============================================================

/** 从 axios / ApiResponse 中提取 data */
function extractData<T>(response: { data: ApiResponse<T> }): T {
  return response.data.data
}

/** 判断是否为后端 API 不可达错误 */
function isNetworkError(error: unknown): boolean {
  return error instanceof Error &&
    (error.message.includes('无法连接') || error.message.includes('网络'))
}

// ============================================================
// Store
// ============================================================

interface TaskStore {
  // 状态
  tasks: Task[]
  currentTask: Task | null
  steps: StepWithDisplay[]
  isLoading: boolean
  error: string | null

  // 方法
  fetchTasks: () => Promise<void>
  createTask: (data: Partial<Task>) => Promise<Task>
  fetchTaskDetail: (taskId: string) => Promise<{ task: Task; steps: StepWithDisplay[] }>
  subscribeToTask: (taskId: string) => () => void  // 返回取消订阅函数
  clearError: () => void
}

export const useTaskStore = create<TaskStore>((set) => ({
  tasks: [],
  currentTask: null,
  steps: [],
  isLoading: false,
  error: null,

  // ---- 获取任务列表 ----
  fetchTasks: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.get<ApiResponse<Task[]>>('/tasks')
      set({ tasks: extractData(response), isLoading: false })
    } catch (err) {
      // API 不可达时降级为 mock 数据
      if (isNetworkError(err)) {
        console.warn('[TaskStore] 后端不可达，使用 mock 数据:', (err as Error).message)
        set({ tasks: MOCK_TASKS, isLoading: false })
        return
      }
      set({ isLoading: false, error: (err as Error).message })
    }
  },

  // ---- 创建任务 ----
  createTask: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const payload = {
        title: data.title ?? '新任务',
        description: data.description ?? '',
        priority: data.priority ?? 'medium',
        assignedAgents: data.assignedAgents ?? [],
        dependencies: data.dependencies ?? [],
      }
      const response = await apiClient.post<ApiResponse<Task>>('/tasks', payload)
      const newTask = extractData(response)
      set((s) => ({ tasks: [newTask, ...s.tasks], isLoading: false }))
      return newTask
    } catch (err) {
      // 降级：本地创建 mock 任务
      if (isNetworkError(err)) {
        console.warn('[TaskStore] 后端不可达，使用本地 mock:', (err as Error).message)
        const newTask: Task = {
          id: `task-${Date.now()}`,
          title: data.title ?? '新任务',
          description: data.description ?? '',
          status: 'pending',
          priority: data.priority ?? 'medium',
          assignedAgents: data.assignedAgents ?? [],
          dependencies: data.dependencies ?? [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }
        set((s) => ({ tasks: [newTask, ...s.tasks], isLoading: false }))
        return newTask
      }
      set({ isLoading: false, error: (err as Error).message })
      throw err
    }
  },

  // ---- 获取任务详情（含步骤） ----
  fetchTaskDetail: async (taskId) => {
    set({ isLoading: true, error: null })
    try {
      // 获取任务详情
      const response = await apiClient.get<ApiResponse<Task>>(`/tasks/${taskId}`)
      const task = extractData(response)

      // 步骤数据：尝试从后端获取；如果后端不返回 steps 字段，用 mock
      // 后端API设计：GET /tasks/{id} 返回任务详情，步骤可能通过SSE获取
      const steps: StepWithDisplay[] = (response.data as unknown as Record<string, unknown>).steps
        ? ((response.data as unknown as Record<string, unknown>).steps as StepWithDisplay[])
        : MOCK_STEPS.filter((s) => s.taskId === taskId)

      set({ currentTask: task, steps, isLoading: false })
      return { task, steps }
    } catch (err) {
      // 降级：使用 mock 数据
      if (isNetworkError(err)) {
        console.warn('[TaskStore] 后端不可达，使用 mock 数据:', (err as Error).message)
        const task = MOCK_TASKS.find((t) => t.id === taskId) ?? null
        if (!task) {
          set({ isLoading: false, error: '任务未找到' })
          throw new Error('任务未找到', { cause: err })
        }
        const steps = MOCK_STEPS.filter((s) => s.taskId === taskId)
        set({ currentTask: task, steps, isLoading: false })
        return { task, steps }
      }
      set({ isLoading: false, error: (err as Error).message })
      throw err
    }
  },

  // ---- 订阅任务的 SSE 流（返回取消订阅函数） ----
  subscribeToTask: (taskId) => {
    let eventSource: EventSource | null = null

    try {
      eventSource = createSSEConnection(`/tasks/${taskId}/stream`, {
        onOpen: () => {
          if (import.meta.env.DEV) {
            console.log(`[SSE] 已连接任务流: ${taskId}`)
          }
        },

        onMessage: (data) => {
          // 后端 SSE 推送的数据格式：
          // { type: 'step_update', step: StepWithDisplay }
          // { type: 'task_update', task: Task }
          const event = data as {
            type: string
            step?: StepWithDisplay
            task?: Task
          }

          if (event.type === 'step_update' && event.step) {
            set((s) => {
              const idx = s.steps.findIndex((st) => st.id === event.step!.id)
              if (idx >= 0) {
                const updated = [...s.steps]
                updated[idx] = event.step!
                return { steps: updated }
              }
              return { steps: [...s.steps, event.step!].sort((a, b) => a.order - b.order) }
            })
          }

          if (event.type === 'task_update' && event.task) {
            set((s) => {
              // 更新 currentTask（如果当前查看的就是这个任务）
              if (s.currentTask?.id === event.task!.id) {
                return { currentTask: event.task! }
              }
              // 同时更新 tasks 列表中的对应项
              return {
                tasks: s.tasks.map((t) =>
                  t.id === event.task!.id ? event.task! : t,
                ),
              }
            })
          }
        },

        onError: () => {
          // SSE 连接错误（通常是后端未就绪），静默处理
          // 数据已通过 fetchTaskDetail 加载到 store
        },
      })
    } catch {
      // 浏览器不支持 SSE 或创建失败
      if (import.meta.env.DEV) {
        console.warn('[SSE] 无法创建任务流连接，将仅使用已加载数据')
      }
    }

    // 返回取消订阅函数
    return () => {
      if (eventSource) {
        eventSource.close()
        if (import.meta.env.DEV) {
          console.log(`[SSE] 已断开任务流: ${taskId}`)
        }
      }
    }
  },

  // ---- 清除错误 ----
  clearError: () => set({ error: null }),
}))

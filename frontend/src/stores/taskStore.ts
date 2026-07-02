import { create } from 'zustand'
import type { Task, TaskStatus, ApiResponse, TaskStep } from '../types'
import apiClient, { createSSEConnection } from '../api/client'
import { toTask, toTaskStatus, toTaskStep, unwrapApiData } from '../api/tasks'

// ============================================================
// 展示类型（用于时间线视觉区分）
// ============================================================

export type StepDisplayType = 'thought' | 'action' | 'observation' | 'final' | 'error'

export type StepWithDisplay = TaskStep

export type TaskStreamStatus = 'connecting' | 'connected' | 'disconnected'

// ============================================================
// 状态标签 & 颜色映射（被页面组件直接引用）
// ============================================================

export const STATUS_COLORS: Record<TaskStatus, string> = {
  pending:   'bg-semantic-pending/10 text-semantic-pending border-semantic-pending/20',
  planning:  'bg-semantic-planning/10 text-semantic-planning border-semantic-planning/20',
  executing: 'bg-semantic-executing/10 text-semantic-executing border-semantic-executing/20',
  completed: 'bg-semantic-completed/10 text-semantic-completed border-semantic-completed/20',
  failed:    'bg-semantic-failed/10 text-semantic-failed border-semantic-failed/20',
  cancelled: 'bg-semantic-cancelled/10 text-semantic-cancelled border-semantic-cancelled/20',
}

export const STATUS_LABELS: Record<TaskStatus, string> = {
  pending:   '待处理',
  planning:  '规划中',
  executing: '执行中',
  completed: '已完成',
  failed:    '失败',
  cancelled: '已取消',
}

export const STEP_TYPE_COLORS: Record<StepDisplayType, string> = {
  thought:     'border-semantic-thought/30 bg-semantic-thought/10 text-semantic-thought',
  action:      'border-semantic-action/30 bg-semantic-action/10 text-semantic-action',
  observation: 'border-semantic-observation/30 bg-semantic-observation/10 text-semantic-observation',
  final:       'border-semantic-final/30 bg-semantic-final/10 text-semantic-final',
  error:       'border-semantic-error/30 bg-semantic-error/10 text-semantic-error',
}

export const STEP_TYPE_LABELS: Record<StepDisplayType, string> = {
  thought:     'thought',
  action:      'action',
  observation: 'observation',
  final:       'final',
  error:       'error',
}

// ============================================================
// API 响应类型（辅助函数内部使用）
// ============================================================

function compareTimelineSteps(a: StepWithDisplay, b: StepWithDisplay): number {
  const orderDelta = a.order - b.order
  if (orderDelta !== 0) return orderDelta

  const aTime = a.startedAt ?? a.completedAt ?? ''
  const bTime = b.startedAt ?? b.completedAt ?? ''
  const timeDelta = aTime.localeCompare(bTime)
  if (timeDelta !== 0) return timeDelta

  return a.id.localeCompare(b.id)
}

function sortTimelineSteps(steps: StepWithDisplay[]): StepWithDisplay[] {
  return [...steps].sort(compareTimelineSteps)
}

type RawRecord = Record<string, unknown>

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
  streamStatus: TaskStreamStatus

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
  streamStatus: 'disconnected',

  // ---- 获取任务列表 ----
  fetchTasks: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.get<ApiResponse<unknown[]> | unknown[]>('/tasks')
      const tasks = unwrapApiData(response.data).map(toTask)
      set({ tasks, isLoading: false })
    } catch (err) {
      const message = err instanceof Error ? err.message : '加载 Task 失败'
      set({ tasks: [], isLoading: false, error: message })
    }
  },

  // ---- 创建任务 ----
  createTask: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const payload = {
        title: data.title ?? '新任务',
        description: data.description ?? '',
      }
      const response = await apiClient.post<ApiResponse<unknown> | unknown>('/tasks', payload)
      const newTask = toTask(unwrapApiData(response.data))
      set((s) => ({ tasks: [newTask, ...s.tasks], isLoading: false }))
      return newTask
    } catch (err) {
      const message = err instanceof Error ? err.message : '创建 Task 失败'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  // ---- 获取任务详情（含步骤） ----
  fetchTaskDetail: async (taskId) => {
    set({ isLoading: true, error: null })
    try {
      // 获取任务详情
      const response = await apiClient.get<ApiResponse<RawRecord> | RawRecord>(`/tasks/${taskId}`)
      const rawDetail = unwrapApiData(response.data)
      const task = toTask(rawDetail)

      // Step timeline only reflects persisted backend data and live SSE updates.
      const rawSteps = Array.isArray(rawDetail.steps)
        ? rawDetail.steps
        : []
      const steps = sortTimelineSteps(rawSteps.map(toTaskStep))

      set({ currentTask: task, steps, isLoading: false })
      return { task, steps }
    } catch (err) {
      const message = err instanceof Error ? err.message : '加载 Task 详情失败'
      set({ currentTask: null, steps: [], isLoading: false, error: message })
      throw err
    }
  },

  // ---- 订阅任务的 SSE 流（返回取消订阅函数） ----
  subscribeToTask: (taskId) => {
    let eventSource: EventSource | null = null
    set({ streamStatus: 'connecting' })

    try {
      eventSource = createSSEConnection(`/tasks/${taskId}/stream`, {
        onOpen: () => {
          set({ streamStatus: 'connected' })
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
            step?: unknown
            task?: unknown
            status?: TaskStatus
          }

          if (event.type === 'step_update' && event.step) {
            const nextStep = toTaskStep(event.step)
            set((s) => {
              const idx = s.steps.findIndex((st) => st.id === nextStep.id)
              if (idx >= 0) {
                const updated = [...s.steps]
                updated[idx] = nextStep
                return { steps: sortTimelineSteps(updated) }
              }
              return {
                steps: sortTimelineSteps([...s.steps, nextStep]),
              }
            })
          }

          if ((event.type === 'task_update' || event.type === 'done') && event.task) {
            const nextTask = toTask(event.task)
            set((s) => {
              // 更新 currentTask（如果当前查看的就是这个任务）
              if (s.currentTask?.id === nextTask.id) {
                return {
                  currentTask: nextTask,
                  tasks: s.tasks.map((t) => t.id === nextTask.id ? nextTask : t),
                }
              }
              // 同时更新 tasks 列表中的对应项
              return {
                tasks: s.tasks.map((t) =>
                  t.id === nextTask.id ? nextTask : t,
                ),
              }
            })
          }

          if (event.type === 'done' && !event.task && event.status) {
            set((s) => ({
              currentTask: s.currentTask
                ? { ...s.currentTask, status: toTaskStatus(event.status) }
                : s.currentTask,
              tasks: s.tasks.map((t) =>
                t.id === taskId ? { ...t, status: toTaskStatus(event.status) } : t,
              ),
            }))
          }
        },

        onError: () => {
          set({ streamStatus: 'disconnected' })
          // SSE 连接错误（通常是后端未就绪），静默处理
          // 数据已通过 fetchTaskDetail 加载到 store
        },
      })
    } catch {
      set({ streamStatus: 'disconnected' })
      // 浏览器不支持 SSE 或创建失败
      if (import.meta.env.DEV) {
        console.warn('[SSE] 无法创建任务流连接，将仅使用已加载数据')
      }
    }

    // 返回取消订阅函数
    return () => {
      if (eventSource) {
        eventSource.close()
        set({ streamStatus: 'disconnected' })
        if (import.meta.env.DEV) {
          console.log(`[SSE] 已断开任务流: ${taskId}`)
        }
      }
    }
  },

  // ---- 清除错误 ----
  clearError: () => set({ error: null }),
}))

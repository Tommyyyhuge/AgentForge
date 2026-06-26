/**
 * AgentForge API 客户端
 * 
 * 基于 axios 的 HTTP 客户端，提供：
 * - 统一的请求/响应拦截器
 * - 错误处理
 * - SSE (Server-Sent Events) 连接封装
 * - 类型安全的 API 方法
 * 
 * 当后端 API 不可用时，自动降级为 mock 数据（通过各 store 层实现）
 */

import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
} from 'axios'
import type { ApiResponse, ApiError } from '../types'

// ============================================================
// 配置
// ============================================================

/** API 基础路径（开发环境通过 vite proxy 转发到 localhost:8000） */
const BASE_URL = '/api/v1'

/** 请求超时时间（毫秒） */
const REQUEST_TIMEOUT = 30_000

// ============================================================
// Axios 实例
// ============================================================

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================================
// 请求拦截器
// ============================================================

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 从 localStorage 读取持久化的 JWT token（与 authStore persist 共享同一 key）
    try {
      const raw = localStorage.getItem('agentforge-auth')
      if (raw) {
        const parsed = JSON.parse(raw) as { state?: { token?: string } }
        const token = parsed?.state?.token
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      }
    } catch {
      // 解析失败静默忽略，不附加 token
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

// ============================================================
// 响应拦截器
// ============================================================

apiClient.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    // 直接返回 axios response，由各 store 层提取 response.data
    return response
  },
  (error: AxiosError<ApiError>) => {
    // 统一错误处理：提取后端错误信息
    let message = '网络请求失败，请检查连接'

    if (error.response) {
      // 服务器返回了错误响应
      const { status, data } = error.response
      const apiError = data as ApiError | undefined

      if (apiError?.error?.message) {
        message = apiError.error.message
      } else {
        // 根据 HTTP 状态码给出中文提示
        const statusMessages: Record<number, string> = {
          400: '请求参数有误',
          401: '未授权，请先登录',
          403: '无权限访问该资源',
          404: '请求的资源不存在',
          409: '资源冲突',
          422: '请求数据验证失败',
          429: '请求过于频繁，请稍后重试',
          500: '服务器内部错误',
          502: '网关错误',
          503: '服务暂时不可用',
          504: '网关超时',
        }
        message = statusMessages[status] ?? `服务器错误 (${status})`
      }

      // 开发环境打印详细错误
      if (import.meta.env.DEV) {
        console.error(
          `[API Error] ${status}`,
          apiError ?? error.response.data,
        )
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应（网络问题）
      message = '无法连接到服务器，请确认后端已启动'
    }

    return Promise.reject(new Error(message))
  },
)

// ============================================================
// SSE (Server-Sent Events) 连接封装
// ============================================================

/** SSE 连接配置 */
export interface SSEConfig {
  /** 收到消息时的回调 */
  onMessage: (data: unknown, eventType?: string) => void
  /** 连接打开时的回调 */
  onOpen?: () => void
  /** 发生错误时的回调 */
  onError?: (error: Event) => void
  /** 每个事件的解析器，默认 JSON.parse */
  parse?: (data: string) => unknown
}

/**
 * 创建 SSE 连接
 * 
 * @param path - API 路径（相对于 /api/v1），例如 '/tasks/task-1/stream'
 * @param config - SSE 配置
 * @returns EventSource 实例，调用方负责在适当时机关闭
 * 
 * @example
 * ```ts
 * const es = createSSEConnection('/tasks/123/stream', {
 *   onMessage: (data) => console.log('收到:', data),
 *   onError: (e) => console.error('SSE错误:', e),
 * })
 * // 组件卸载时
 * es.close()
 * ```
 */
export function createSSEConnection(
  path: string,
  config: SSEConfig,
): EventSource {
  const fullUrl = `${BASE_URL}${path}`
  const eventSource = new EventSource(fullUrl)
  const parse = config.parse ?? JSON.parse

  const handleMessage = (eventType: string, event: MessageEvent) => {
    try {
      const data = parse(event.data as string)
      config.onMessage(data, eventType)
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('[SSE] 数据解析失败:', event.data, err)
      }
    }
  }

  eventSource.onopen = () => {
    config.onOpen?.()
  }

  eventSource.onmessage = (event: MessageEvent) => {
    handleMessage('message', event)
  }

  for (const eventType of ['step', 'done', 'agent_state']) {
    eventSource.addEventListener(eventType, (event) => {
      handleMessage(eventType, event as MessageEvent)
    })
  }

  eventSource.onerror = (error: Event) => {
    config.onError?.(error)
    
    // CLOSED 状态表示连接已终止
    if (eventSource.readyState === EventSource.CLOSED) {
      if (import.meta.env.DEV) {
        console.warn('[SSE] 连接已关闭')
      }
    }
  }

  return eventSource
}

// ============================================================
// 导出
// ============================================================

export default apiClient

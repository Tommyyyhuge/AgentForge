/**
 * AgentForge 认证状态管理
 *
 * 基于 Zustand + persist 中间件，提供：
 * - JWT token 持久化（localStorage）
 * - 登录 / 注册 / 登出 / 获取用户信息
 * - 统一的 loading / error 状态
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { ApiResponse, ApiError } from '../types'
import apiClient from '../api/client'

// ============================================================
// 类型
// ============================================================

/** 认证用户 */
export interface AuthUser {
  id: string
  username: string
  email: string
}

/** Auth Store 状态 & Actions */
export interface AuthState {
  // ---------- 状态 ----------
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // ---------- Actions ----------
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, email?: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
  clearError: () => void
}

// ============================================================
// 持久化 storage key（与 api/client.ts 拦截器保持一致）
// ============================================================

export const AUTH_STORAGE_KEY = 'agentforge-auth'

// ============================================================
// 辅助函数
// ============================================================

/** 从 axios 响应中提取 data — 兼容包裹/非包裹格式 */
function extractData<T>(response: { data: ApiResponse<T> | T }): T {
  const body = response.data as any
  // FastAPI 直接返回模型时，body 就是数据本身
  // 包裹格式: { success: true, data: {...} }
  return body?.success ? body.data : body
}

/** 从 ApiError 中提取可读错误信息 */
function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const axiosErr = err as { response?: { data?: ApiError } }
    const apiError = axiosErr.response?.data
    if (apiError?.error?.message) {
      return apiError.error.message
    }
  }
  if (err instanceof Error) {
    return err.message
  }
  return '操作失败，请稍后重试'
}

// ------- Store

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // ------- 初始状态 -------
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // ------- 登录 -------
      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.post('/auth/login', {
            username,
            password,
          })
          const data = extractData(response) as any
          // 后端返回: { access_token, token_type }
          const token = data.access_token
          set({ token, isAuthenticated: true, isLoading: false, error: null })
          // 登录后获取用户信息
          await get().fetchUser()
        } catch (err) {
          set({ isLoading: false, error: extractErrorMessage(err) })
          throw err
        }
      },

      // ------- 注册 -------
      register: async (username: string, password: string, email?: string) => {
        set({ isLoading: true, error: null })
        try {
          await apiClient.post('/auth/register', {
            username,
            password,
            email: email || '',
          })
          // 注册成功，自动登录
          await get().login(username, password)
        } catch (err) {
          set({ isLoading: false, error: extractErrorMessage(err) })
          throw err
        }
      },

      // ------- 登出 -------
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        })
      },

      // ------- 获取当前用户信息 -------
      fetchUser: async () => {
        const { token } = get()
        if (!token) {
          set({ isAuthenticated: false, user: null })
          return
        }

        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.get<ApiResponse<AuthUser>>('/auth/me')
          set({
            user: extractData(response),
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (err) {
          // token 失效或过期 → 清除认证状态
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: extractErrorMessage(err),
          })
        }
      },

      // ------- 清除错误 -------
      clearError: () => set({ error: null }),
    }),
    {
      name: AUTH_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      // 仅持久化 user 和 token，不持久化 isLoading/error
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)

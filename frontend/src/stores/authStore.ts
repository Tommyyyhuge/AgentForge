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
import type { ApiResponse } from '../types'
import apiClient from '../api/client'
import { getApiErrorMessage, unwrapApiData } from '../api/envelope'

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

interface TokenResponse {
  access_token: string
  token_type: string
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
          const data = unwrapApiData<TokenResponse>(response.data)
          // 后端返回: { access_token, token_type }
          const token = data.access_token
          set({ token, isAuthenticated: true, isLoading: false, error: null })
          // 登录后获取用户信息
          await get().fetchUser()
        } catch (err) {
          set({ isLoading: false, error: getApiErrorMessage(err) })
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
          set({ isLoading: false, error: getApiErrorMessage(err) })
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
            user: unwrapApiData(response.data),
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (err) {
          // /auth/me 失败时不立即登出 — 可能只是 token 尚未持久化
          // 仅清除 user，保留 token 和认证状态供重试
          set({
            user: null,
            isLoading: false,
            error: getApiErrorMessage(err),
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

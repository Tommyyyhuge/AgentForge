import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export type Theme = 'light' | 'dark' | 'system'

export interface ThemeStore {
  /** 用户选择的主题 */
  theme: Theme
  /** 实际应用的主题（system 模式下解析后的值） */
  resolvedTheme: 'light' | 'dark'
  /** 切换主题 */
  setTheme: (theme: Theme) => void
}

const STORAGE_KEY = 'agentforge-theme'

/**
 * 应用主题到 DOM
 */
function applyTheme(theme: 'light' | 'dark') {
  const html = document.documentElement
  if (theme === 'dark') {
    html.classList.add('dark')
  } else {
    html.classList.remove('dark')
  }
}

/**
 * 获取系统主题偏好
 */
function getSystemTheme(): 'light' | 'dark' {
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

/**
 * 解析主题（处理 system 模式）
 */
function resolveTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') {
    return getSystemTheme()
  }
  return theme
}

/**
 * 初始化主题（在应用启动时调用，避免 FOUC）
 */
export function initTheme() {
  // 从 localStorage 读取主题偏好
  let theme: Theme = 'system'
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (parsed.state?.theme) {
        theme = parsed.state.theme
      }
    }
  } catch {
    // 解析失败则使用默认值
  }

  // 立即应用主题（在 React 渲染前）
  applyTheme(resolveTheme(theme))

  // 监听系统主题变化
  if (theme === 'system') {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', (e) => {
      applyTheme(e.matches ? 'dark' : 'light')
    })
  }
}

/**
 * 主题状态管理
 *
 * 使用 Zustand + persist 持久化主题偏好
 */
export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'system',
      resolvedTheme: 'dark',

      setTheme: (theme: Theme) => {
        const resolved = resolveTheme(theme)
        applyTheme(resolved)
        set({ theme, resolvedTheme: resolved })
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        // 持久化恢复后，重新应用主题
        if (state) {
          const resolved = resolveTheme(state.theme)
          applyTheme(resolved)
          state.resolvedTheme = resolved
        }
      },
    }
  )
)

/**
 * useTheme Hook
 *
 * 便捷访问主题状态和切换方法
 */
export function useTheme() {
  const { theme, resolvedTheme, setTheme } = useThemeStore()

  return {
    theme,
    resolvedTheme,
    isDark: resolvedTheme === 'dark',
    setTheme,
    toggleTheme: () => {
      if (theme === 'dark') setTheme('light')
      else if (theme === 'light') setTheme('dark')
      else setTheme(getSystemTheme() === 'dark' ? 'light' : 'dark')
    },
  }
}

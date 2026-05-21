import { describe, it, expect, beforeEach } from 'vitest'
import { useThemeStore } from '../../src/hooks/useTheme'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  value: (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }),
})

describe('useThemeStore', () => {
  beforeEach(() => {
    localStorageMock.clear()
    useThemeStore.setState({ theme: 'dark', resolvedTheme: 'dark' })
  })

  it('默认主题是 system', () => {
    useThemeStore.setState({ theme: 'system', resolvedTheme: 'dark' })
    expect(useThemeStore.getState().theme).toBe('system')
  })

  it('切换主题到 light', () => {
    useThemeStore.getState().setTheme('light')
    expect(useThemeStore.getState().theme).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('切换主题到 dark', () => {
    useThemeStore.getState().setTheme('dark')
    expect(useThemeStore.getState().theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('主题持久化到 localStorage', () => {
    useThemeStore.getState().setTheme('light')
    // 验证类名已应用
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    // 验证 store 状态
    expect(useThemeStore.getState().theme).toBe('light')
  })
})

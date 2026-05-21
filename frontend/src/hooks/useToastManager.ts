import { useState, useCallback } from 'react'
import type { ToastItem, ToastOptions } from '../components/ui/Toast'
import { setToastCallback } from '../utils/toast'

/**
 * Toast 状态管理 Hook
 *
 * 用于管理 Toast 通知的显示和隐藏
 */
export function useToastManager() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const addToast = useCallback((options: ToastOptions) => {
    const id = `toast-${Date.now()}-${Math.floor(Math.random() * 1000000).toString(36)}`
    const duration = options.duration ?? 3000

    const newToast: ToastItem = {
      id,
      type: options.type,
      message: options.message,
      duration,
    }

    setToasts((prev) => [...prev.slice(-4), newToast]) // 最多 5 个

    // 自动关闭
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, duration)
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const clearToasts = useCallback(() => {
    setToasts([])
  }, [])

  // 注册全局回调
  setToastCallback(addToast)

  return { toasts, addToast, removeToast, clearToasts }
}

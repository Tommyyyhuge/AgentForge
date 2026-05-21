import type { ToastOptions } from '../components/ui/Toast'

let addToastCallback: ((options: ToastOptions) => void) | null = null

export function setToastCallback(cb: (options: ToastOptions) => void) {
  addToastCallback = cb
}

export function toast(options: ToastOptions): void
export function toast(message: string, type?: 'success' | 'error' | 'warning' | 'info'): void
export function toast(
  arg1: ToastOptions | string,
  arg2?: 'success' | 'error' | 'warning' | 'info'
): void {
  if (!addToastCallback) {
    console.warn('Toast: 未设置回调，请确保 ToastProvider 已挂载')
    return
  }

  if (typeof arg1 === 'string') {
    addToastCallback({
      type: arg2 ?? 'info',
      message: arg1,
    })
  } else {
    addToastCallback(arg1)
  }
}

// 便捷方法
toast.success = (message: string, duration?: number) =>
  toast({ type: 'success', message, duration })
toast.error = (message: string, duration?: number) =>
  toast({ type: 'error', message, duration })
toast.warning = (message: string, duration?: number) =>
  toast({ type: 'warning', message, duration })
toast.info = (message: string, duration?: number) =>
  toast({ type: 'info', message, duration })

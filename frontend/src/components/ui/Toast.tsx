import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastItem {
  id: string
  type: ToastType
  message: string
  duration: number
}

export interface ToastOptions {
  type: ToastType
  message: string
  duration?: number
}

// ============================================================
// Toast 单条组件
// ============================================================

const typeConfig = {
  success: {
    icon: <CheckCircle2 className="h-5 w-5 text-emerald-400" />,
    bg: 'bg-emerald-500/10 border-emerald-500/20',
    progress: 'bg-emerald-400',
  },
  error: {
    icon: <AlertCircle className="h-5 w-5 text-red-400" />,
    bg: 'bg-red-500/10 border-red-500/20',
    progress: 'bg-red-400',
  },
  warning: {
    icon: <AlertTriangle className="h-5 w-5 text-amber-400" />,
    bg: 'bg-amber-500/10 border-amber-500/20',
    progress: 'bg-amber-400',
  },
  info: {
    icon: <Info className="h-5 w-5 text-forge-400" />,
    bg: 'bg-forge-500/10 border-forge-500/20',
    progress: 'bg-forge-400',
  },
} as const

interface ToastProps {
  toast: ToastItem
  onRemove: (id: string) => void
}

function Toast({ toast, onRemove }: ToastProps) {
  const config = typeConfig[toast.type]

  return (
    <motion.div
      layout
      className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-forge border p-4 shadow-forge ${config.bg}`}
      initial={{ opacity: 0, x: 100, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      <div className="mt-0.5 shrink-0">{config.icon}</div>
      <div className="flex-1">
        <p className="text-sm text-white">{toast.message}</p>
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className="shrink-0 rounded p-1 text-neutral-400 transition-colors hover:bg-white/5 hover:text-white"
      >
        <X className="h-4 w-4" />
      </button>

      {/* 进度条 */}
      <motion.div
        className={`absolute bottom-0 left-0 h-0.5 rounded-full ${config.progress}`}
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: toast.duration / 1000, ease: 'linear' }}
        style={{ position: 'absolute', bottom: 0 }}
      />
    </motion.div>
  )
}

// ============================================================
// Toast 容器组件
// ============================================================

export interface ToastContainerProps {
  toasts: ToastItem[]
  onRemove: (id: string) => void
}

export default function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div
      className="fixed right-4 top-4 z-[60] flex flex-col gap-3"
      aria-live="polite"
      aria-atomic="true"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} onRemove={onRemove} />
        ))}
      </AnimatePresence>
    </div>
  )
}

// 注意：useToastManager 已移到 hooks/useToastManager.ts

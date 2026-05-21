import { memo } from 'react'
import { motion } from 'framer-motion'

export interface LoadingProps {
  /** 变体类型 */
  variant: 'spinner' | 'skeleton' | 'overlay'
  /** 提示文字 */
  text?: string
  /** 自定义 className */
  className?: string
  /** Skeleton 行数（仅 variant='skeleton' 有效） */
  rows?: number
}

/**
 * Loading 加载态组件
 *
 * 变体：
 * - spinner: 转圈加载（适合按钮内、小区域）
 * - skeleton: 骨架屏（适合页面初始加载）
 * - overlay: 全屏遮罩（适合提交表单、切换页面）
 */
function Loading({
  variant,
  text,
  className = '',
  rows = 3,
}: LoadingProps) {
  if (variant === 'spinner') {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`}>
        <svg
          className="h-5 w-5 animate-spin text-forge-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        {text && <span className="text-sm text-neutral-400">{text}</span>}
      </div>
    )
  }

  if (variant === 'skeleton') {
    return (
      <div className={`space-y-3 ${className}`}>
        {Array.from({ length: rows }).map((_, i) => (
          <motion.div
            key={i}
            className="h-4 rounded bg-neutral-700/50"
            style={{ width: `${85 + ((i * 37) % 15)}%` }}
            animate={{ opacity: [0.5, 0.8, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </div>
    )
  }

  // overlay
  return (
    <div
      className={`absolute inset-0 z-40 flex flex-col items-center justify-center bg-surface-bg/80 backdrop-blur-sm ${className}`}
    >
      <Loading variant="spinner" />
      {text && (
        <p className="mt-3 text-sm text-neutral-400">{text}</p>
      )}
    </div>
  )
}

export default memo(Loading)

/**
 * 页面级 Loading（全屏居中）
 */
export function PageLoading({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="flex h-[50vh] items-center justify-center">
      <Loading variant="spinner" text={text} />
    </div>
  )
}

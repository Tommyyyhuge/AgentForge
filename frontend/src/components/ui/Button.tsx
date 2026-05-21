import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** 变体 */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg'
  /** 是否加载中 */
  isLoading?: boolean
  /** 左侧图标 */
  leftIcon?: ReactNode
  /** 右侧图标 */
  rightIcon?: ReactNode
}

const variantClasses = {
  primary:
    'bg-forge-500 text-white hover:bg-forge-700 active:bg-forge-900 disabled:bg-forge-500/50',
  secondary:
    'bg-white/10 text-white hover:bg-white/15 active:bg-white/20 disabled:bg-white/5 disabled:text-neutral-500',
  ghost:
    'text-neutral-400 hover:bg-white/5 hover:text-white active:bg-white/10 disabled:text-neutral-600',
  danger:
    'bg-red-500/10 text-red-400 hover:bg-red-500/20 active:bg-red-500/30 disabled:bg-red-500/5 disabled:text-red-400/50',
} as const

const sizeClasses = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-5 py-2.5 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
} as const

/**
 * Button 按钮组件
 *
 * 特性：
 * - 4 种变体：primary、secondary、ghost、danger
 * - 3 种尺寸：sm、md、lg
 * - 支持 loading 状态（内置 Spinner）
 * - 支持图标前缀/后缀
 * - Framer Motion 点击缩放动画
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  children,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || isLoading

  return (
    <motion.button
      className={`
        inline-flex items-center justify-center rounded-forge font-medium
        transition-colors duration-200
        focus:outline-none focus:ring-2 focus:ring-forge-500/50 focus:ring-offset-2 focus:ring-offset-surface-bg
        disabled:cursor-not-allowed
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `}
      whileTap={isDisabled ? undefined : { scale: 0.97 }}
      disabled={isDisabled}
      {...(props as React.ComponentPropsWithoutRef<typeof motion.button>)}
    >
      {isLoading && (
        <Loader2 className="h-4 w-4 animate-spin" />
      )}
      {!isLoading && leftIcon}
      {children}
      {!isLoading && rightIcon}
    </motion.button>
  )
}

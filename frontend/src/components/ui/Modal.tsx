import { type ReactNode, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

export interface ModalProps {
  /** 是否显示 */
  isOpen: boolean
  /** 关闭回调 */
  onClose: () => void
  /** 标题 */
  title?: string
  /** 描述 */
  description?: string
  /** 内容 */
  children: ReactNode
  /** 底部操作区 */
  footer?: ReactNode
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  /** 点击遮罩层是否关闭（默认 true） */
  closeOnOverlay?: boolean
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
} as const

/**
 * Modal 模态对话框
 *
 * 特性：
 * - Framer Motion 进入/退出动画（fade + scale）
 * - ESC 键关闭
 * - 点击遮罩层关闭（可配置）
 * - 打开时锁定背景滚动
 * - 自动聚焦第一个可交互元素
 */
export default function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  closeOnOverlay = true,
}: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  // ESC 键关闭
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      // 锁定背景滚动
      const originalOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      return () => {
        document.removeEventListener('keydown', handleKeyDown)
        document.body.style.overflow = originalOverflow
      }
    }
  }, [isOpen, onClose])

  // 自动聚焦
  useEffect(() => {
    if (isOpen && contentRef.current) {
      const focusable = contentRef.current.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      focusable?.focus()
    }
  }, [isOpen])

  function handleOverlayClick(e: React.MouseEvent) {
    if (closeOnOverlay && e.target === overlayRef.current) {
      onClose()
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={overlayRef}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.6)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={handleOverlayClick}
          role="dialog"
          aria-modal="true"
        >
          <motion.div
            ref={contentRef}
            className={`w-full ${sizeClasses[size]} rounded-forge border border-surface-border bg-surface-light shadow-forge-lg`}
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* 头部 */}
            {(title || description) && (
              <div className="flex items-start justify-between border-b border-surface-border px-6 py-4">
                <div>
                  {title && (
                    <h3 className="text-lg font-semibold text-white">{title}</h3>
                  )}
                  {description && (
                    <p className="mt-1 text-sm text-neutral-400">{description}</p>
                  )}
                </div>
                <button
                  onClick={onClose}
                  className="ml-4 rounded-lg p-1 text-neutral-400 transition-colors hover:bg-white/5 hover:text-white"
                  aria-label="关闭"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            )}

            {/* 内容 */}
            <div className="px-6 py-4">{children}</div>

            {/* 底部 */}
            {footer && (
              <div className="flex items-center justify-end gap-3 border-t border-surface-border px-6 py-4">
                {footer}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

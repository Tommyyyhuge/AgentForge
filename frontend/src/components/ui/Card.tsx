import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  /** 自定义 className */
  className?: string
  /** 是否禁用 hover 阴影效果 */
  noHover?: boolean
  /** 点击回调 */
  onClick?: () => void
}

export default function Card({ children, className = '', noHover = false, onClick }: CardProps) {
  return (
    <div
      className={`forge-card ${noHover ? '' : 'cursor-pointer'} ${className}`}
      onClick={onClick}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter') onClick() } : undefined}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  )
}

import { type ReactNode, memo } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  noHover?: boolean
  onClick?: () => void
}

function Card({ children, className = '', noHover = false, onClick }: CardProps) {
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

export default memo(Card)
